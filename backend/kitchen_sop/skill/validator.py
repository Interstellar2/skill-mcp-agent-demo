"""SKILL 内容校验：工具存在性、参数 Schema 匹配."""

import json
from typing import Any, Dict, List


class SkillValidationError(Exception):
    """SKILL 校验失败时抛出的异常."""

    pass


def _tool_name_to_key(tool_name: str) -> str:
    """将可能带有 server__tool 格式的名称转换为规范 key."""
    return tool_name.replace("__", ".")


def _find_tool(tools, tool_name: str):
    """在 MCP 工具列表中查找指定名称的工具."""
    key = _tool_name_to_key(tool_name)
    for t in tools:
        if hasattr(t, "name") and _tool_name_to_key(t.name) == key:
            return t
    return None


def validate_skill_metadata_tools(declared: List[str], mcp_tools: List[Any]) -> None:
    """校验 Skill frontmatter 中声明的工具是否都存在.

    Args:
        declared: Skill metadata 中声明的工具名列表.
        mcp_tools: MCP 服务器返回的工具列表.

    Raises:
        SkillValidationError: 有声明的工具不存在时抛出.
    """
    missing = []
    available = {_tool_name_to_key(t.name): t.name for t in mcp_tools if hasattr(t, "name")}
    for name in declared:
        if _tool_name_to_key(name) not in available:
            missing.append(name)
    if missing:
        raise SkillValidationError(
            f"Skill 声明了未在 MCP 服务器注册的工具: {', '.join(missing)}"
        )


def _get_nested(schema: Dict[str, Any], *keys: str) -> Any:
    """安全获取嵌套字典值."""
    cur = schema
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


def _schema_for_tool(tool) -> Dict[str, Any]:
    """统一获取工具的输入 Schema."""
    schema = getattr(tool, "inputSchema", None) or {}
    if not isinstance(schema, dict):
        try:
            schema = json.loads(schema)
        except Exception:
            schema = {}
    return schema


def validate_skill_steps(steps: List[Dict[str, Any]], mcp_tools: List[Any]) -> None:
    """校验 SKILL 步骤中的工具调用是否合法.

    检查项：
    1. 每个步骤引用的工具必须存在.
    2. 每个参数必须在工具 schema 的 properties 中声明（如果 schema 存在）.
    3. 必填参数必须提供.

    Args:
        steps: 从 SOP 解析出的步骤列表.
        mcp_tools: MCP 服务器返回的工具列表.

    Raises:
        SkillValidationError: 校验失败时抛出，包含所有错误信息.
    """
    errors: List[str] = []

    for step in steps:
        tool_name = step.get("tool_name")
        arguments = step.get("arguments", {})
        step_idx = step.get("step_index") or steps.index(step) + 1

        tool = _find_tool(mcp_tools, tool_name)
        if tool is None:
            errors.append(f"步骤 {step_idx}: 工具 '{tool_name}' 未在 MCP 服务器注册")
            continue

        schema = _schema_for_tool(tool)
        properties = _get_nested(schema, "properties") or {}
        required = _get_nested(schema, "required") or []

        for key in arguments.keys():
            if properties and key not in properties:
                errors.append(
                    f"步骤 {step_idx}: 工具 '{tool_name}' 不接受参数 '{key}'"
                )

        for req in required:
            if req not in arguments:
                errors.append(
                    f"步骤 {step_idx}: 工具 '{tool_name}' 缺少必填参数 '{req}'"
                )

    if errors:
        raise SkillValidationError(
            "Skill 校验失败:\n" + "\n".join(f"- {e}" for e in errors)
        )
