"""Parallel 模式：分析步骤依赖关系，将无依赖的步骤分组并行执行."""

import asyncio
import logging
from typing import Awaitable, Callable, Dict, List, Optional, Set

from ..mcp_client import get_mcp_tools
from ..mcp_pool import MCPConnectionPool
from ..tracker import RunTracker
from .base import SkillExecutorContext, execute_step

logger = logging.getLogger("kitchen_agent")

EventBroadcaster = Optional[Callable[[str, dict], Awaitable[None]]]


def _build_dag(steps: List[dict]) -> Dict[int, Set[int]]:
    """构建步骤依赖图，返回 step_index -> set of dependent step_indices.

    依赖规则：
    1. 默认情况下，所有步骤按顺序依赖前一个步骤
    2. 如果某步骤有 parallel_group_id，同组内步骤无互相依赖
    3. 如果某步骤有 depends_on，则显式依赖指定组或步骤完成后才能执行
    """
    n = len(steps)
    deps: Dict[int, Set[int]] = {i + 1: set() for i in range(n)}

    group_last_step: Dict[str, int] = {}
    for i, step in enumerate(steps, 1):
        gid = step.get("parallel_group_id")
        if gid:
            group_last_step[gid] = i

    for i, step in enumerate(steps, 1):
        gid = step.get("parallel_group_id")
        explicit_deps = step.get("depends_on", []) or []

        if explicit_deps:
            for dep in explicit_deps:
                if dep in group_last_step:
                    deps[i].add(group_last_step[dep])
                else:
                    try:
                        dep_idx = int(dep)
                        if 1 <= dep_idx < i:
                            deps[i].add(dep_idx)
                    except ValueError:
                        pass
        elif gid:
            if i > 1:
                prev_gid = steps[i - 2].get("parallel_group_id")
                if prev_gid != gid:
                    deps[i].add(i - 1)
        else:
            if i > 1:
                deps[i].add(i - 1)

    for i in range(2, n + 1):
        if not deps[i] and not steps[i - 1].get("parallel_group_id"):
            deps[i].add(i - 1)

    return deps


def _topological_batches(steps: List[dict], deps: Dict[int, Set[int]]) -> List[List[int]]:
    """将步骤按拓扑排序分组，同批次内步骤可以并行执行."""
    n = len(steps)
    if n == 0:
        return []

    completed: Set[int] = set()
    batches: List[List[int]] = []

    while len(completed) < n:
        ready = []
        for i in range(1, n + 1):
            if i in completed:
                continue
            if all(d in completed for d in deps[i]):
                ready.append(i)

        if not ready:
            raise ValueError("检测到循环依赖，无法调度")

        batches.append(ready)
        completed.update(ready)

    return batches


async def run_parallel_mode(
    skill_name: str = "tomato_egg",
    skills_dir=None,
    variables: Optional[dict] = None,
    tracker: Optional[RunTracker] = None,
    event_broadcaster: EventBroadcaster = None,
    mcp_pool: Optional[MCPConnectionPool] = None,
):
    """Parallel 模式：解析 SOP 中的并行标记，按 DAG 拓扑排序并行执行."""
    async with SkillExecutorContext(
        skill_name, skills_dir=skills_dir, variables=variables
    ) as ctx:
        steps = ctx.steps

        deps = _build_dag(steps)
        try:
            batches = _topological_batches(steps, deps)
        except ValueError as e:
            logger.error(f"并行调度失败: {e}")
            return

        logger.info("=" * 60)
        logger.info("⚡ Parallel 模式: 并行执行")
        logger.info(f"   Skill: {skill_name}")
        logger.info(f"   共 {len(steps)} 个步骤，分为 {len(batches)} 个执行批次")
        for bi, batch in enumerate(batches, 1):
            step_str = ", ".join(f"#{i}" for i in batch)
            logger.info(f"   批次 {bi}: {step_str}")
        logger.info("=" * 60)

        async def _execute(session):
            await ctx.validate_steps(session)
            t = tracker or RunTracker(skill_name, mode="parallel", variables=ctx.merged_vars)
            if tracker is None:
                async with t:
                    await _run_batches(t, session, steps, batches, event_broadcaster)
            else:
                await _run_batches(t, session, steps, batches, event_broadcaster)

        if mcp_pool is not None:
            await _execute(mcp_pool.session)
        else:
            async with get_mcp_tools() as (tools, session):
                logger.info(
                    f"🔧 已连接 MCP 服务器，可用工具: {', '.join(t.name for t in tools)}"
                )
                await _execute(session)


async def _run_batches(
    tracker: RunTracker,
    session,
    steps: list,
    batches: List[List[int]],
    event_broadcaster: EventBroadcaster,
):
    logger.info(f"   Run ID: {tracker.record.run_id}")

    for batch_idx, batch in enumerate(batches, 1):
        logger.info(f"\n🏃 批次 {batch_idx}/{len(batches)}: 并行执行步骤 {batch}")

        if event_broadcaster:
            await event_broadcaster(
                "batch_start",
                {
                    "batch_index": batch_idx,
                    "step_indices": batch,
                    "total_batches": len(batches),
                },
            )

        async def _execute_one(step_index: int) -> tuple:
            step = steps[step_index - 1]
            tool_name = step["tool_name"]
            arguments = step["arguments"]
            group_id = step.get("parallel_group_id")

            step_rec = tracker.start_step(step_index, tool_name, arguments)
            if group_id:
                step_rec.parallel_group_id = group_id

            logger.info(f"📌 步骤 {step_index}: [{tool_name}] args={arguments}")
            try:
                text = await execute_step(
                    session, tracker, step_rec, tool_name, arguments,
                    event_broadcaster=event_broadcaster,
                )
                logger.info(f"   ➡️  [{step_index}] {text or '(无返回内容)'}")
                return (step_index, "success", text)
            except Exception as e:
                logger.error(f"   ❌ [{step_index}] 调用失败: {e}")
                return (step_index, "error", str(e))

        results = await asyncio.gather(
            *[_execute_one(i) for i in batch], return_exceptions=True
        )

        if event_broadcaster:
            await event_broadcaster(
                "batch_finish",
                {
                    "batch_index": batch_idx,
                    "step_indices": batch,
                },
            )

        errors = [r for r in results if isinstance(r, Exception) or (isinstance(r, tuple) and r[1] == "error")]
        if errors:
            logger.error("批次执行出错，停止后续步骤")
            break

    logger.info("=" * 60)
    logger.info(f"🎉 并行执行完毕！{tracker.record.skill_name} 已完成~")
    logger.info("=" * 60)
