"""查询类命令实现."""

from kitchen_sop.tracker import RunTracker


def _print_run(run):
    """美观打印一次执行记录."""
    print(f"Run ID:    {run.run_id}")
    print(f"Skill:     {run.skill_name}")
    print(f"Mode:      {run.mode}")
    print(f"Status:    {run.overall_status}")
    print(f"Variables: {run.variables or '-'}")
    print(f"Started:   {run.started_at}")
    print(f"Ended:     {run.ended_at or '-'}")
    if run.resumed_from:
        print(f"Resumed:   from {run.resumed_from}")
    if run.rollback_to_step:
        print(f"Rollback:  to step {run.rollback_to_step}")
    print("-" * 60)
    for s in run.steps:
        dur = f"{s.duration_ms}ms" if s.duration_ms else "-"
        extra = ""
        if s.parallel_group_id:
            extra += f" [group:{s.parallel_group_id}]"
        if s.checkpoint_id:
            extra += f" [cp:{s.checkpoint_id}]"
        if s.human_approval:
            extra += f" [hitl:{s.human_approval.decision}]"
        print(f"  [{s.step_index:2}] {s.tool_name:20} ({s.status:7}, {dur:>8}){extra}")
        print(f"       args: {s.arguments}")
        if s.result_text:
            print(f"       result: {s.result_text[:100]}")
        if s.error_message:
            print(f"       error:  {s.error_message}")
    print("-" * 60)


def list_runs_command():
    """列出最近执行记录."""
    runs = RunTracker.list_runs(limit=20)
    if not runs:
        print("暂无执行记录。")
        return
    print(f"{'Run ID':<12} {'Mode':<12} {'Skill':<15} {'Status':<8} {'Started'}")
    print("-" * 70)
    for r in runs:
        print(
            f"{r.run_id:<12} {r.mode:<12} {r.skill_name:<15} {r.overall_status:<8} {r.started_at}"
        )


def replay_run_command(run_id: str):
    """回放某次历史执行."""
    run = RunTracker.load_run(run_id)
    if not run:
        print(f"未找到执行记录: {run_id}")
        return
    _print_run(run)
