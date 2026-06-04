"""
Kitchen SOP Demo - Skill + MCP 演示入口

Usage:
    python main.py --demo                         # 无需 API Key，按 SOP 顺序执行
    python main.py --agent                        # 需要 OPENAI_API_KEY，LLM 自主决策
    python main.py --demo --var egg_count=5       # 传入变量覆盖默认值
    python main.py --list-runs                    # 查看最近执行记录
    python main.py --replay abc123                # 回放某次执行
    python main.py                                # 默认运行 demo 模式

配置:
    在项目根目录创建 .env 文件（参考 .env.example）
"""

import asyncio
import argparse
import logging
import os

from kitchen_sop.config import load_env, DEFAULT_MODEL, DEFAULT_SKILL, LOGS_DIR
from kitchen_sop.logging_utils import setup_logging
from kitchen_sop.executors.demo import run_demo_mode
from kitchen_sop.tracker import RunTracker


# 加载 .env（只需在入口处执行一次）
load_env()

# 配置日志
logger = setup_logging("kitchen_agent", log_dir=str(LOGS_DIR))


def _parse_var_args(var_list: list[str] | None) -> dict:
    """将 --var key=value 列表解析为字典."""
    result = {}
    if not var_list:
        return result
    for item in var_list:
        if "=" not in item:
            logger.warning(f"忽略格式错误的变量: {item}（应为 key=value）")
            continue
        key, val = item.split("=", 1)
        result[key.strip()] = val.strip()
    return result


def _print_run(run):
    """美观打印一次执行记录."""
    print(f"Run ID:    {run.run_id}")
    print(f"Skill:     {run.skill_name}")
    print(f"Mode:      {run.mode}")
    print(f"Status:    {run.overall_status}")
    print(f"Variables: {run.variables or '-'}")
    print(f"Started:   {run.started_at}")
    print(f"Ended:     {run.ended_at or '-'}")
    print("-" * 60)
    for s in run.steps:
        dur = f"{s.duration_ms}ms" if s.duration_ms else "-"
        print(f"  [{s.step_index:2}] {s.tool_name:20} ({s.status:7}, {dur:>8})")
        print(f"       args: {s.arguments}")
        if s.result_text:
            print(f"       result: {s.result_text[:100]}")
        if s.error_message:
            print(f"       error:  {s.error_message}")
    print("-" * 60)


async def main():
    parser = argparse.ArgumentParser(description="Kitchen SOP 演示")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="运行 Demo 模式：直接按 SOP 步骤顺序调用工具（无需 API Key）",
    )
    parser.add_argument(
        "--agent",
        action="store_true",
        help="运行 Agent 模式：使用 LangChain + LLM 自主决策（需要 OPENAI_API_KEY）",
    )
    parser.add_argument(
        "--skill",
        type=str,
        default=DEFAULT_SKILL,
        help=f"要加载的 Skill 名称（默认: {DEFAULT_SKILL}）",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=os.environ.get("MODEL", DEFAULT_MODEL),
        help=f"Agent 模式使用的模型（默认从 .env 读取 MODEL，否则为 {DEFAULT_MODEL}）",
    )
    parser.add_argument(
        "--var",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="传入变量覆盖 Skill 默认值（可多次使用，如 --var egg_count=5）",
    )
    parser.add_argument(
        "--list-runs",
        action="store_true",
        help="列出最近执行记录",
    )
    parser.add_argument(
        "--replay",
        type=str,
        metavar="RUN_ID",
        help="回放某次历史执行（不调用真实工具）",
    )

    args = parser.parse_args()

    # --- 查询类命令（不启动执行） ---
    if args.list_runs:
        runs = RunTracker.list_runs(limit=20)
        if not runs:
            print("暂无执行记录。")
            return
        print(f"{'Run ID':<12} {'Mode':<6} {'Skill':<15} {'Status':<8} {'Started'}")
        print("-" * 70)
        for r in runs:
            print(
                f"{r.run_id:<12} {r.mode:<6} {r.skill_name:<15} {r.overall_status:<8} {r.started_at}"
            )
        return

    if args.replay:
        run = RunTracker.load_run(args.replay)
        if not run:
            print(f"未找到执行记录: {args.replay}")
            return
        _print_run(run)
        return

    # --- 正常执行模式 ---
    variables = _parse_var_args(args.var)

    # 1. 模式解析
    mode = "agent" if args.agent else "demo"
    if mode == "agent" and not os.environ.get("OPENAI_API_KEY"):
        logger.warning("未设置 OPENAI_API_KEY，自动切换到 Demo 模式")
        logger.info(
            "提示: 在项目根目录创建 .env 文件，写入 OPENAI_API_KEY='your-key'"
        )
        mode = "demo"

    # 2. 执行路由
    kwargs = {"skill_name": args.skill, "variables": variables}
    if mode == "agent":
        # 延迟导入，避免 Demo 模式依赖 LangChain
        from kitchen_sop.executors.agent import run_agent_mode

        kwargs["model"] = args.model
        await run_agent_mode(**kwargs)
    else:
        await run_demo_mode(**kwargs)


if __name__ == "__main__":
    asyncio.run(main())
