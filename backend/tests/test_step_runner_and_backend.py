"""Tests for StepRunner variable parsing and state backend round-trip."""

import asyncio
import json
import os
import tempfile
from pathlib import Path

import pytest

from kitchen_sop.executors.step_runner import StepRunner
from kitchen_sop.executors.hooks.variable_hook import _parse_output_variables
from kitchen_sop.executors.checkpoint_strategies import (
    get_resume_strategy,
    get_rollback_strategy,
)
from kitchen_sop.executors.checkpoint_strategies.rollback_compensating import (
    RollbackCompensatingStrategy,
)
from kitchen_sop.tracker.state_backend.local_json import LocalJSONStateBackend
from kitchen_sop.tracker import RunTracker
from kitchen_sop.tracker.models import RunRecord, Checkpoint, StepRecord
from kitchen_sop.tracker.checkpoint_service import CheckpointService
from kitchen_sop.tracker.checkpoint import CheckpointManager
from kitchen_sop.tracker.retention import (
    CheckpointRetentionPolicy,
    RetentionPolicyEnforcer,
)
from kitchen_sop.executors.step_runner import build_step_hooks
from kitchen_sop.executors.hooks import EventHook, CheckpointHook, VariableHook
from kitchen_sop.executors.agent.message_recorder import AgentMessageRecorder
from kitchen_sop.executors.agent.message_reconstructor import reconstruct_lc_messages
from kitchen_sop.api.orchestrator import launch_run
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage


class MockResult:
    def __init__(self, text):
        self.content = [MockContent(text)]


class MockContent:
    def __init__(self, text):
        self.text = text


class MockSession:
    def __init__(self, result_text):
        self._result_text = result_text

    async def call_tool(self, tool_name, arguments=None):
        return MockResult(self._result_text)


class TestStepRunner:
    def test_compensation_context_extracted_for_json_result(self):
        async def _run():
            backend = LocalJSONStateBackend(runs_dir=Path(tempfile.mkdtemp()))
            tracker = RunTracker(
                skill_name="test", mode="demo", backend=backend
            )
            async with tracker:
                step_rec = tracker.start_step(1, "heat_pan", {"duration": 30})
                session = MockSession(json.dumps({"transaction_id": "tx-123"}))
                hooks = build_step_hooks(tracker, enable_checkpoint=True)
                runner = StepRunner(session, tracker, hooks=hooks)
                await runner.run(
                    step_rec,
                    "heat_pan",
                    {"duration": 30},
                    compensator={"tool_name": "season", "arguments": {}},
                )
                assert step_rec.compensation_context == {"transaction_id": "tx-123"}

        asyncio.run(_run())

    def test_compensation_context_not_set_without_compensator(self):
        async def _run():
            backend = LocalJSONStateBackend(runs_dir=Path(tempfile.mkdtemp()))
            tracker = RunTracker(
                skill_name="test", mode="demo", backend=backend
            )
            async with tracker:
                step_rec = tracker.start_step(1, "heat_pan", {"duration": 30})
                session = MockSession(json.dumps({"transaction_id": "tx-123"}))
                hooks = build_step_hooks(tracker, enable_checkpoint=True)
                runner = StepRunner(session, tracker, hooks=hooks)
                await runner.run(step_rec, "heat_pan", {"duration": 30})
                assert step_rec.compensation_context is None

        asyncio.run(_run())

    def test_hook_execution_order(self):
        async def _run():
            backend = LocalJSONStateBackend(runs_dir=Path(tempfile.mkdtemp()))
            tracker = RunTracker(skill_name="test", mode="demo", backend=backend)
            async with tracker:
                step_rec = tracker.start_step(1, "heat_pan", {"duration": 30})
                session = MockSession(json.dumps({"temperature": 200}))

                events = []

                class TracingHook:
                    async def on_before(self, runner, step_rec, tool_name, arguments):
                        events.append("before")
                    async def on_after(self, runner, step_rec, tool_name, arguments, result_text):
                        events.append("after")
                    async def on_error(self, runner, step_rec, tool_name, arguments, error):
                        events.append("error")

                hooks = [TracingHook()] + build_step_hooks(tracker, enable_checkpoint=False)
                runner = StepRunner(session, tracker, hooks=hooks)
                await runner.run(
                    step_rec, "heat_pan", {"duration": 30}, output_variable="temperature"
                )
                assert events == ["before", "after"]
                assert tracker.record.variables == {"temperature": 200}

        asyncio.run(_run())

    def test_checkpoint_service_saves_before_after_error(self):
        async def _run():
            backend = LocalJSONStateBackend(runs_dir=Path(tempfile.mkdtemp()))
            tracker = RunTracker(skill_name="test", mode="resumable", backend=backend)
            cp_manager = CheckpointManager(backend=backend)
            cp_service = CheckpointService(tracker, cp_manager)
            async with tracker:
                step_rec = tracker.start_step(1, "heat_pan", {"duration": 30})
                cp_before = await cp_service.save_before_step(
                    step_index=1, tool_name="heat_pan", arguments={"duration": 30}
                )
                assert cp_before is not None
                assert cp_before.step_status == "before_step"

                cp_after = await cp_service.save_after_step(step=step_rec)
                assert cp_after is not None
                assert cp_after.step_status == "after_step"

                step_rec2 = tracker.start_step(2, "fail", {})
                cp_error = await cp_service.save_on_error(step=step_rec2)
                assert cp_error is not None
                assert cp_error.step_status == "error"

        asyncio.run(_run())


class TestRollbackCompensating:
    def test_compensates_steps_with_context_and_re_executes(self):
        async def _run():
            backend = LocalJSONStateBackend(runs_dir=Path(tempfile.mkdtemp()))
            tracker = RunTracker(skill_name="test", mode="rollback", backend=backend)
            async with tracker:
                orig_steps = [
                    StepRecord(
                        step_index=1,
                        tool_name="cut",
                        arguments={},
                        status="success",
                        compensation_context=None,
                    ),
                    StepRecord(
                        step_index=2,
                        tool_name="heat_pan",
                        arguments={},
                        status="success",
                        compensation_context={"transaction_id": "tx-1"},
                    ),
                    StepRecord(
                        step_index=3,
                        tool_name="plate",
                        arguments={},
                        status="success",
                        compensation_context={"transaction_id": "tx-2"},
                    ),
                ]
                steps = [
                    {"tool_name": "cut", "arguments": {}},
                    {
                        "tool_name": "heat_pan",
                        "arguments": {},
                        "compensator": {
                            "tool_name": "season",
                            "arguments": {"salt": "{{transaction_id}}"},
                        },
                    },
                    {
                        "tool_name": "plate",
                        "arguments": {},
                        "compensator": {
                            "tool_name": "season",
                            "arguments": {"sugar": "{{transaction_id}}"},
                        },
                    },
                ]

                calls = []

                class _Session:
                    async def call_tool(self, tool_name, arguments=None):
                        calls.append((tool_name, arguments))
                        return MockResult(f"done {tool_name}")

                strategy = RollbackCompensatingStrategy()
                await strategy.rollback(
                    tracker, _Session(), steps, 2, None, orig_steps=orig_steps
                )

                # 反向补偿：step 3 然后 step 2
                assert calls[0] == ("season", {"sugar": "tx-2"})
                assert calls[1] == ("season", {"salt": "tx-1"})
                # 正向重执行从 step 2 开始
                assert calls[2] == ("heat_pan", {})
                assert calls[3] == ("plate", {})

        asyncio.run(_run())


class TestStrategyRegistry:
    def test_resume_strategy_order(self):
        # agent 状态应命中 AgentResumeStrategy
        strat = get_resume_strategy({"agent_messages": []})
        assert strat.name == "agent"
        # plan 状态应命中 PlanResumeStrategy
        strat = get_resume_strategy({"plan_steps": []})
        assert strat.name == "plan"
        # parallel 状态应命中 ParallelResumeStrategy
        strat = get_resume_strategy({"batches": []})
        assert strat.name == "parallel"
        # 兜底 sequential
        strat = get_resume_strategy({})
        assert strat.name == "sequential"

    def test_rollback_strategy_selection(self):
        assert get_rollback_strategy(False).name == "rollback_sequential"
        assert get_rollback_strategy(True).name == "rollback_compensating"
    def test_no_text(self):
        assert _parse_output_variables(None) == {}
        assert _parse_output_variables("") == {}

    def test_json_with_output_variable(self):
        text = json.dumps({"result": 42, "temperature": 200})
        assert _parse_output_variables(text, output_variable="temperature") == {"temperature": 200}

    def test_json_with_variables_key(self):
        text = json.dumps({"variables": {"salt": "1小勺", "sugar": "1/2小勺"}})
        assert _parse_output_variables(text) == {"salt": "1小勺", "sugar": "1/2小勺"}

    def test_non_dict_json(self):
        text = json.dumps([1, 2, 3])
        assert _parse_output_variables(text) == {}

    def test_invalid_json(self):
        assert _parse_output_variables("not json") == {}


class TestLocalJSONStateBackend:
    def test_roundtrip_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = LocalJSONStateBackend(runs_dir=Path(tmpdir))
            run = RunRecord.new(skill_name="tomato_egg", mode="demo")
            run.variables = {"egg_count": 3}

            asyncio.run(backend.save_run(run))
            loaded = asyncio.run(backend.load_run(run.run_id))

            assert loaded is not None
            assert loaded.run_id == run.run_id
            assert loaded.skill_name == "tomato_egg"
            assert loaded.mode == "demo"
            assert loaded.variables == {"egg_count": 3}

    def test_list_runs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = LocalJSONStateBackend(runs_dir=Path(tmpdir))
            run1 = RunRecord.new(skill_name="tomato_egg", mode="demo")
            run2 = RunRecord.new(skill_name="kung_pao_chicken", mode="agent")
            asyncio.run(backend.save_run(run1))
            asyncio.run(backend.save_run(run2))

            runs = asyncio.run(backend.list_runs(limit=10))
            run_ids = {r.run_id for r in runs}
            assert run1.run_id in run_ids
            assert run2.run_id in run_ids

    def test_checkpoint_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = LocalJSONStateBackend(runs_dir=Path(tmpdir))
            cp = Checkpoint(
                checkpoint_id="abc123",
                run_id="run456",
                step_index=2,
                step_status="after_step",
                variables={"egg_count": 3},
                step_results=[],
                created_at="2024-01-01T12:00:00",
                executor_state={"plan_steps": []},
            )
            asyncio.run(backend.save_checkpoint(cp))

            loaded = asyncio.run(backend.load_checkpoint("abc123"))
            assert loaded is not None
            assert loaded.checkpoint_id == "abc123"
            assert loaded.run_id == "run456"

            cps = asyncio.run(backend.list_checkpoints("run456"))
            assert len(cps) == 1
            assert cps[0].checkpoint_id == "abc123"

    def test_delete_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = LocalJSONStateBackend(runs_dir=Path(tmpdir))
            run = RunRecord.new(skill_name="tomato_egg", mode="demo")
            asyncio.run(backend.save_run(run))
            asyncio.run(backend.delete_run(run.run_id))
            assert asyncio.run(backend.load_run(run.run_id)) is None

    def test_delete_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = LocalJSONStateBackend(runs_dir=Path(tmpdir))
            cp = Checkpoint(
                checkpoint_id="del001",
                run_id="run001",
                step_index=1,
                step_status="after_step",
                variables={},
                step_results=[],
                created_at="2024-01-01T12:00:00",
            )
            asyncio.run(backend.save_checkpoint(cp))
            asyncio.run(backend.delete_checkpoint("del001"))
            assert asyncio.run(backend.load_checkpoint("del001")) is None


class TestRetentionPolicyEnforcer:
    def test_keep_last_n_and_latest_per_step(self):
        async def _run():
            with tempfile.TemporaryDirectory() as tmpdir:
                backend = LocalJSONStateBackend(runs_dir=Path(tmpdir))
                enforcer = RetentionPolicyEnforcer(backend)
                run_id = "run-ret"
                for i in range(5):
                    cp = Checkpoint(
                        checkpoint_id=f"cp{i:03d}",
                        run_id=run_id,
                        step_index=i + 1,
                        step_status="after_step",
                        variables={},
                        step_results=[],
                        created_at=f"2024-01-01T12:00:0{i}",
                    )
                    await backend.save_checkpoint(cp)
                policy = CheckpointRetentionPolicy(keep_last_n=3, keep_latest_per_step=True)
                await enforcer.apply_policy(run_id, policy)
                remaining = await backend.list_checkpoints(run_id)
                assert len(remaining) == 3
                assert remaining[-1].checkpoint_id == "cp004"

        asyncio.run(_run())

    def test_ttl_cleanup(self):
        async def _run():
            with tempfile.TemporaryDirectory() as tmpdir:
                backend = LocalJSONStateBackend(runs_dir=Path(tmpdir))
                enforcer = RetentionPolicyEnforcer(backend)
                run_id = "run-ttl"
                from datetime import datetime, timedelta
                old = datetime.now() - timedelta(hours=25)
                cp = Checkpoint(
                    checkpoint_id="cp-old",
                    run_id=run_id,
                    step_index=1,
                    step_status="after_step",
                    variables={},
                    step_results=[],
                    created_at=old.isoformat(timespec="seconds"),
                )
                await backend.save_checkpoint(cp)
                policy = CheckpointRetentionPolicy(ttl_hours=24)
                await enforcer.apply_policy(run_id, policy)
                assert await backend.load_checkpoint("cp-old") is None

        asyncio.run(_run())


class TestAgentMessageRecorder:
    def test_records_human_ai_tool_messages(self):
        recorder = AgentMessageRecorder()
        recorder.record_human("hello")
        recorder.record_ai("thought", tool_calls=[{"id": "call1", "name": "tool", "args": {}}])
        recorder.record_tool("result", "call1")
        assert len(recorder.messages) == 3
        assert recorder.messages[0]["type"] == "human"
        assert recorder.messages[1]["type"] == "ai"
        assert recorder.messages[2]["type"] == "tool"

    def test_reconstruct_lc_messages(self):
        messages = [
            {"type": "human", "content": "hi"},
            {"type": "ai", "content": "ok", "tool_calls": [{"id": "c1", "name": "t", "args": {}}]},
            {"type": "tool", "content": "r", "tool_call_id": "c1"},
        ]
        lc = reconstruct_lc_messages(messages)
        assert isinstance(lc[0], HumanMessage)
        assert isinstance(lc[1], AIMessage)
        assert isinstance(lc[2], ToolMessage)


class TestLaunchRun:
    def test_launch_run_lifecycle(self):
        async def _run():
            backend = LocalJSONStateBackend(runs_dir=Path(tempfile.mkdtemp()))
            tracker = RunTracker(skill_name="test", mode="demo", backend=backend)
            await tracker.__aenter__()
            events = []

            async def executor():
                events.append("executed")

            run_id = await launch_run(
                tracker_factory=lambda: tracker,
                executor=executor,
                initial_event={"type": "test_started", "payload": {"x": 1}},
            )
            assert run_id == tracker.record.run_id
            await asyncio.sleep(0.05)
            assert "executed" in events
            loaded = await backend.load_run(run_id)
            assert loaded is not None
            assert loaded.overall_status == "success"

        asyncio.run(_run())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
