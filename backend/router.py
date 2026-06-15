"""执行路由."""

import logging
import os

from kitchen_sop.executors.demo import run_demo_mode

logger = logging.getLogger("kitchen_agent")


def resolve_mode(args) -> str:
    """解析执行模式并检查 API Key."""
    mode = "demo"
    if args.agent:
        mode = "agent"
    elif args.plan_then_execute:
        mode = "plan_then_execute"
    elif args.hitl:
        mode = "hitl"
    elif args.parallel:
        mode = "parallel"
    elif args.resumable:
        mode = "resumable"

    if mode in ("agent", "plan_then_execute") and not os.environ.get("OPENAI_API_KEY"):
        logger.warning("未设置 OPENAI_API_KEY，自动切换到 Demo 模式")
        logger.info(
            "提示: 在项目根目录创建 .env 文件，写入 OPENAI_API_KEY='your-key'"
        )
        mode = "demo"

    return mode


async def route_execution(mode: str, skill_name: str, variables: dict, model: str, enable_checkpoint: bool = False):
    """路由到对应的执行器."""
    kwargs = {"skill_name": skill_name, "variables": variables}

    if mode == "agent":
        from kitchen_sop.executors.agent.agent_runner import run_agent_mode
        kwargs["model"] = model
        kwargs["enable_checkpoint"] = enable_checkpoint
        await run_agent_mode(**kwargs)
    elif mode == "plan_then_execute":
        from kitchen_sop.executors.plan_then_execute import run_plan_then_execute_mode
        kwargs["model"] = model
        kwargs["enable_checkpoint"] = enable_checkpoint
        await run_plan_then_execute_mode(**kwargs)
    elif mode == "hitl":
        from kitchen_sop.executors.hitl import run_hitl_mode
        kwargs["enable_checkpoint"] = enable_checkpoint
        await run_hitl_mode(**kwargs)
    elif mode == "parallel":
        from kitchen_sop.executors.parallel import run_parallel_mode
        kwargs["enable_checkpoint"] = enable_checkpoint
        await run_parallel_mode(**kwargs)
    elif mode == "resumable":
        from kitchen_sop.executors.resumable import run_resumable_mode
        await run_resumable_mode(**kwargs)
    else:
        kwargs["enable_checkpoint"] = enable_checkpoint
        await run_demo_mode(**kwargs)


async def route_resume_rollback(args, backend=None) -> bool:
    """处理 resume / rollback 命令.

    返回 True 表示已处理并应结束程序。
    """
    if backend is None:
        from kitchen_sop.tracker.state_backend import get_state_backend
        backend = get_state_backend()

    if args.resume:
        from kitchen_sop.executors.resume import resume_run
        await resume_run(
            run_id=args.resume,
            checkpoint_id=args.checkpoint_id,
            backend=backend,
        )
        return True

    if args.rollback:
        if args.to_step is None:
            print("错误: --rollback 必须配合 --to-step 使用")
            return True
        from kitchen_sop.executors.rollback import rollback_run
        await rollback_run(
            run_id=args.rollback,
            to_step=args.to_step,
            checkpoint_id=args.checkpoint_id,
            compensate=args.compensate,
            backend=backend,
        )
        return True

    return False
