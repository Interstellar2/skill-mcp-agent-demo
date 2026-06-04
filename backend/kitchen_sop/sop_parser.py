"""SOP Markdown 内容解析：支持工具调用步骤和子流程内联."""

import re
from typing import TYPE_CHECKING, Dict, List, Optional, Set

from .template_engine import render_sop

if TYPE_CHECKING:
    from .skill_manager import SkillsManager


def parse_sop_steps(
    sop_content: str,
    sm: Optional["SkillsManager"] = None,
    variables: Optional[dict] = None,
    _visited: Optional[Set[str]] = None,
) -> List[dict]:
    """从 SOP Markdown 内容中解析出工具调用步骤.

    支持两种标记:
    - **工具**: `tool_name`  → 直接提取参数
    - **子流程**: `skill_name` → 递归加载并内联该 Skill 的步骤

    Args:
        sop_content: SOP Markdown 内容.
        sm: SkillsManager 实例，用于加载子流程.
        variables: 变量字典，用于模板渲染.
        _visited: 内部使用，防止循环引用.

    Returns:
        步骤列表，每个步骤包含 tool_name 和 arguments.
    """
    if _visited is None:
        _visited = set()

    steps = []
    lines = sop_content.splitlines()
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # 匹配工具声明行: **工具**: `cut_ingredient`
        tool_match = re.match(r"\*\*工具\*\*:\s*`?(\w+)`?", line)
        if tool_match:
            tool_name = tool_match.group(1)
            arguments = {}
            i += 1

            # 读取后续参数，直到遇到空行或下一个步骤标题
            while i < len(lines):
                param_line = lines[i].strip()
                if (
                    not param_line
                    or param_line.startswith("### ")
                    or param_line.startswith("## ")
                ):
                    break
                if param_line.startswith("-") and ":" in param_line:
                    # 格式: - key: "value" 或 - key: value
                    param_content = param_line[1:].strip()
                    if ":" in param_content:
                        key, val = param_content.split(":", 1)
                        key = key.strip()
                        val = val.strip().strip('"').strip("'")
                        arguments[key] = val
                i += 1

            # 尝试类型转换
            for key, val in arguments.items():
                if val.lower() == "true":
                    arguments[key] = True
                elif val.lower() == "false":
                    arguments[key] = False
                else:
                    try:
                        arguments[key] = int(val)
                    except ValueError:
                        pass

            steps.append(
                {
                    "tool_name": tool_name,
                    "arguments": arguments,
                }
            )
            continue

        # 匹配子流程声明行: **子流程**: `marinate_meat`
        sub_match = re.match(r"\*\*子流程\*\*:\s*`?(\w+)`?", line)
        if sub_match:
            sub_name = sub_match.group(1)
            if sub_name in _visited:
                raise ValueError(
                    f"检测到子流程循环引用: {' -> '.join(_visited)} -> {sub_name}"
                )

            if sm is None:
                raise ValueError(
                    f"SOP 引用了子流程 '{sub_name}'，但未提供 SkillsManager"
                )

            sub_sop = sm.activate_skill(sub_name)
            if sub_sop is None:
                raise ValueError(f"找不到子流程 Skill: {sub_name}")

            # 递归解析子流程（同样做变量渲染）
            rendered_sub = render_sop(sub_sop, variables or {})
            _visited.add(sub_name)
            try:
                sub_steps = parse_sop_steps(
                    rendered_sub, sm=sm, variables=variables, _visited=_visited
                )
            finally:
                _visited.discard(sub_name)

            steps.extend(sub_steps)
            i += 1
            continue

        i += 1

    return steps
