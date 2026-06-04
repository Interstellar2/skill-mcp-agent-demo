"""Parallel 模式：分析步骤依赖关系，将无依赖的步骤分组并行执行."""

import asyncio
import logging
from typing import Dict, List, Optional, Set

from ..mcp_client import get_mcp_tools
from ..tracker import RunTracker
from .base import SkillExecutorContext, execute_step

logger = logging.getLogger("kitchen_agent")


def _build_dag(steps: List[dict]) -> Dict[int, Set[int]]:
    """构建步骤依赖图，返回 step_index -> set of dependent step_indices.

    依赖规则：
    1. 默认情况下，所有步骤按顺序依赖前一个步骤
    2. 如果某步骤有 parallel_group_id，同组内步骤无互相依赖
    3. 如果某步骤有 depends_on，则显式依赖指定组或步骤完成后才能执行
    """
    # step_index 从 1 开始
    n = len(steps)
    deps: Dict[int, Set[int]] = {i + 1: set() for i in range(n)}

    # 建立 group -> last step index 映射
    group_last_step: Dict[str, int] = {}
    for i, step in enumerate(steps, 1):
        gid = step.get("parallel_group_id")
        if gid:
            group_last_step[gid] = i

    # 计算每个步骤的依赖
    for i, step in enumerate(steps, 1):
        gid = step.get("parallel_group_id")
        explicit_deps = step.get("depends_on", []) or []

        if explicit_deps:
            # 显式依赖：依赖指定 group 的最后一个步骤
            for dep in explicit_deps:
                if dep in group_last_step:
                    deps[i].add(group_last_step[dep])
                else:
                    # 可能是步骤索引
                    try:
                        dep_idx = int(dep)
                        if 1 <= dep_idx < i:
                            deps[i].add(dep_idx)
                    except ValueError:
                        pass
        elif gid:
            # 有 parallel_group_id 但没有显式依赖：默认依赖之前所有非本组的步骤
            # 实际上更简单的策略：依赖上一个 "批次的最后一个步骤"
            # 这里采用：如果前面有非本组的步骤，依赖最后一个非本组的步骤
            if i > 1:
                prev_gid = steps[i - 2].get("parallel_group_id")
                if prev_gid != gid:
                    # 找到前一个不同组的最后一个步骤（就是 i-1）
                    deps[i].add(i - 1)
                else:
                    # 同组内不互相依赖（并行）
                    pass
        else:
            # 没有 group 标记：顺序依赖前一步
            if i > 1:
                deps[i].add(i - 1)

    # 兜底：没有 group 标记且没有任何依赖的步骤，默认顺序依赖前一步
    for i in range(2, n + 1):
        if not deps[i] and not steps[i - 1].get("parallel_group_id"):
            deps[i].add(i - 1)

    return deps


def _topological_batches(steps: List[dict], deps: Dict[int, Set[int]]) -> List[List[int]]:
    """将步骤按拓扑排序分组，同批次内步骤可以并行执行.

    返回: [[step_index1, step_index2], [step_index3], ...]
    """
    n = len(steps)
    if n == 0:
        return []

    completed: Set[int] = set()
    batches: List[List[int]] = []

    while len(completed) < n:
        # 找出所有依赖已满足的步骤
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
):
    """Parallel 模式：解析 SOP 中的并行标记，按 DAG 拓扑排序并行执行."""
    async with SkillExecutorContext(
        skill_name, skills_dir=skills_dir, variables=variables
    ) as ctx:
        steps = ctx.steps

        # 构建 DAG 和调度批次
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

        async with get_mcp_tools() as (tools, session):
            logger.info(
                f"🔧 已连接 MCP 服务器，可用工具: {', '.join(t.name for t in tools)}"
            )

            async with RunTracker(
                skill_name, mode="parallel", variables=ctx.merged_vars
            ) as tracker:
                logger.info(f"   Run ID: {tracker.record.run_id}")

                for batch_idx, batch in enumerate(batches, 1):
                    logger.info(f"\n🏃 批次 {batch_idx}/{len(batches)}: 并行执行步骤 {batch}")

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
                            text = await execute_step(session, tracker, step_rec, tool_name, arguments)
                            logger.info(f"   ➡️  [{step_index}] {text or '(无返回内容)'}")
                            return (step_index, "success", text)
                        except Exception as e:
                            logger.error(f"   ❌ [{step_index}] 调用失败: {e}")
                            return (step_index, "error", str(e))

                    # 并行执行当前批次
                    results = await asyncio.gather(
                        *[_execute_one(i) for i in batch], return_exceptions=True
                    )

                    # 检查是否有错误
                    errors = [r for r in results if isinstance(r, Exception) or (isinstance(r, tuple) and r[1] == "error")]
                    if errors:
                        logger.error("批次执行出错，停止后续步骤")
                        break

                logger.info("=" * 60)
                logger.info(f"🎉 并行执行完毕！{skill_name} 已完成~")
                logger.info("=" * 60)
