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
    python main.py --rollback abc123 --to-step 3 --compensate  # 补偿回滚
    python main.py --demo --var egg_count=5       # 传入变量覆盖默认值
    python main.py --list-runs                    # 查看最近执行记录
    python main.py --replay abc123                # 回放某次执行
    python main.py                                # 默认运行 demo 模式

配置:
    在项目根目录创建 .env 文件（参考 .env.example）
    支持分布式状态后端：
      - local_json（默认）
      - S3：设置 KITCHEN_STATE_BACKEND=s3 及 KITCHEN_S3_BUCKET/AWS 凭证
      - Redis：设置 KITCHEN_STATE_BACKEND=redis 及 KITCHEN_REDIS_URL
"""

import asyncio
import logging

from kitchen_sop.config import load_env, LOGS_DIR
from kitchen_sop.logging_utils import setup_logging
from kitchen_sop.mcp_pool import get_mcp_pool
from kitchen_sop.skill import (
    SkillGenerationError,
    generate_skill_draft,
    preview_skill_draft,
    save_skill,
)
from kitchen_sop.tracker.state_backend import get_state_backend
from cli import build_parser, _parse_var_args
from commands import _list_runs_async, _replay_run_async, skill_stats_command
from router import resolve_mode, route_execution, route_resume_rollback

# 加载 .env（只需在入口处执行一次）
load_env()

# 配置日志
logger = setup_logging("kitchen_agent", log_dir=str(LOGS_DIR))


async def _input(prompt: str) -> str:
    """在线程中运行 input，避免阻塞事件循环."""
    return await asyncio.to_thread(input, prompt)


async def run_generate_skill_wizard():
    """交互式 Skill 生成向导."""
    print("\n=== Skill 生成向导 ===")
    print("根据自然语言描述生成 SKILL.md 文件。\n")

    description = await _input("请输入菜品或流程描述（如：生成一份青椒炒肉 SOP）：\n> ")
    if not description.strip():
        print("描述不能为空，已退出。")
        return

    model = await _input("请输入模型名称（直接回车使用默认）：\n> ")
    model = model.strip() or None

    async with get_mcp_pool() as pool:
        mcp_tools = pool.mcp_tools
        print(f"\n已加载 {len(mcp_tools)} 个 MCP 工具，正在生成草稿...")

        try:
            draft = await generate_skill_draft(
                prompt=description,
                model=model,
                mcp_tools=mcp_tools,
            )
        except SkillGenerationError as e:
            print(f"生成失败: {e}")
            return
        except Exception as e:
            print(f"生成失败: {e}")
            return

    print("\n----- 生成的 SKILL.md 草稿 -----")
    print(draft)
    print("--------------------------------\n")

    preview_choice = await _input("是否预览解析结果？[y/N]: ")
    if preview_choice.strip().lower() in ("y", "yes"):
        preview = preview_skill_draft(draft, mcp_tools=mcp_tools)
        print("\n----- 预览结果 -----")
        print(f"元数据: {preview.get('metadata')}")
        print(f"步骤数: {len(preview.get('steps', []))}")
        if preview.get("errors"):
            print("错误:")
            for err in preview["errors"]:
                print(f"  - {err}")
        if preview.get("step_errors"):
            print("步骤错误:")
            for err in preview["step_errors"]:
                print(f"  - 步骤 {err.get('step_index')}: {err.get('message')}")
        print(f"校验通过: {preview.get('valid')}")
        print("--------------------\n")

    name = await _input("请输入保存的 skill 名称（如 green_pepper_pork）：\n> ")
    name = name.strip()
    if not name:
        print("未输入名称，已退出。")
        return

    try:
        path = save_skill(name=name, markdown=draft, overwrite=False)
    except SkillGenerationError as e:
        print(f"保存失败: {e}")
        return
    except Exception as e:
        print(f"保存失败: {e}")
        return

    print(f"\n保存成功: {path}")
    print(f"可通过以下命令验证：python backend/main.py --skill {name} --demo")


async def main():
    parser = build_parser()
    args = parser.parse_args()

    backend = get_state_backend()

    # --- 查询类命令（不启动执行） ---
    if args.list_runs:
        await _list_runs_async(backend=backend)
        return

    if args.replay:
        await _replay_run_async(args.replay, backend=backend)
        return

    if args.skill_stats:
        skill_stats_command()
        return

    # --- Skill 生成向导 ---
    if args.generate_skill:
        await run_generate_skill_wizard()
        return

    # --- Resume / Rollback（不需要 skill 参数，从记录中推断） ---
    if await route_resume_rollback(args, backend=backend):
        return

    # --- 正常执行模式 ---
    variables = _parse_var_args(args.var)

    # 1. 模式解析（优先级按参数出现顺序）
    mode = resolve_mode(args)

    # 2. 执行路由
    await route_execution(mode, args.skill, variables, args.model, args.enable_checkpoint)


if __name__ == "__main__":
    asyncio.run(main())
