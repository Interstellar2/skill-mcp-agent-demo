"""Kitchen SOP Demo - Skill + MCP 演示入口

Usage:
    python main.py --demo                         # 无需 API Key，按 SOP 顺序执行
    python main.py --agent                        # 需要 OPENAI_API_KEY，LLM 自主决策
    python main.py --plan-then-execute            # Plan-then-Execute 模式
    python main.py --hitl                         # Human-in-the-Loop 模式
    python main.py --parallel                     # 并行执行模式
    python main.py --resumable                    # 可续作模式（自动保存检查点）
    python main.py --resume abc123                # 从检查点恢复执行
    python main.py --rollback abc123 --to-step 3  # 回滚到步骤3重新执行
    python main.py --demo --var egg_count=5       # 传入变量覆盖默认值
    python main.py --list-runs                    # 查看最近执行记录
    python main.py --replay abc123                # 回放某次执行
    python main.py                                # 默认运行 demo 模式

配置:
    在项目根目录创建 .env 文件（参考 .env.example）
"""

import asyncio
import logging

from kitchen_sop.config import load_env, LOGS_DIR
from kitchen_sop.logging_utils import setup_logging
from cli import build_parser, _parse_var_args
from commands import list_runs_command, replay_run_command
from router import resolve_mode, route_execution, route_resume_rollback

# 加载 .env（只需在入口处执行一次）
load_env()

# 配置日志
logger = setup_logging("kitchen_agent", log_dir=str(LOGS_DIR))


async def main():
    parser = build_parser()
    args = parser.parse_args()

    # --- 查询类命令（不启动执行） ---
    if args.list_runs:
        list_runs_command()
        return

    if args.replay:
        replay_run_command(args.replay)
        return

    # --- Resume / Rollback（不需要 skill 参数，从记录中推断） ---
    if await route_resume_rollback(args):
        return

    # --- 正常执行模式 ---
    variables = _parse_var_args(args.var)

    # 1. 模式解析（优先级按参数出现顺序）
    mode = resolve_mode(args)

    # 2. 执行路由
    await route_execution(mode, args.skill, variables, args.model)


if __name__ == "__main__":
    asyncio.run(main())
