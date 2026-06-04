"""CLI 参数解析."""

import argparse
import os

from kitchen_sop.config import DEFAULT_MODEL, DEFAULT_SKILL


def _parse_var_args(var_list: list[str] | None) -> dict:
    """将 --var key=value 列表解析为字典."""
    result = {}
    if not var_list:
        return result
    for item in var_list:
        if "=" not in item:
            print(f"忽略格式错误的变量: {item}（应为 key=value）")
            continue
        key, val = item.split("=", 1)
        result[key.strip()] = val.strip()
    return result


def build_parser() -> argparse.ArgumentParser:
    """构建并返回命令行参数解析器."""
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
        "--plan-then-execute",
        action="store_true",
        dest="plan_then_execute",
        help="运行 Plan-then-Execute 模式：LLM 先生成计划，再严格按计划执行",
    )
    parser.add_argument(
        "--hitl",
        action="store_true",
        help="运行 Human-in-the-Loop 模式：关键步骤前暂停等待人工确认",
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="运行 Parallel 模式：按 DAG 拓扑排序并行执行无依赖步骤",
    )
    parser.add_argument(
        "--resumable",
        action="store_true",
        help="运行 Resumable 模式：顺序执行并自动保存检查点（用于断电续作）",
    )
    parser.add_argument(
        "--resume",
        type=str,
        metavar="RUN_ID",
        help="从指定 run 的最新检查点恢复执行",
    )
    parser.add_argument(
        "--rollback",
        type=str,
        metavar="RUN_ID",
        help="回滚到指定步骤重新执行（需配合 --to-step）",
    )
    parser.add_argument(
        "--to-step",
        type=int,
        metavar="N",
        help="回滚目标步骤（配合 --rollback 使用）",
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
        help=f"Agent / Plan 模式使用的模型（默认从 .env 读取 MODEL，否则为 {DEFAULT_MODEL}）",
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
    return parser
