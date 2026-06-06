"""SKILL 验证器：在 SOP 执行前检查工具存在性与参数类型匹配.

支持两阶段验证:
- Phase 1: 工具存在性（tool_name 是否在 MCP Server 中注册）
- Phase 2: 参数 Schema 匹配（必填参数、基础 JSON Schema 类型检查）
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("kitchen_agent")


class SkillValidationError(ValueError):
    """Skill 验证失败的统一异常.

    收集所有发现的问题后一次性抛出，方便开发者/用户批量修复。
    """

    pass


def _type_matches(value: Any, json_schema_type: str) -> bool:
    """检查 Python 值是否匹配 JSON Schema 的基础类型.

    支持的类型映射:
        string  -> str
        integer -> int
        number  -> int | float
        boolean -> bool
        array   -> list
        object  -> dict
        null    -> NoneType
    """
    type_map = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "array": list,
        "object": dict,
        "null": type(None),
    }
    expected = type_map.get(json_schema_type)
    if expected is None:
        return True  # 未知 schema 类型，不拦截
    return isinstance(value, expected)


def _validate_step_arguments(
    step_idx: int,
    tool_name: str,
    arguments: Dict[str, Any],
    schema: Optional[Dict[str, Any]],
) -> List[str]:
    """验证单步参数是否符合工具的 JSON Schema.

    目前检查项:
    1. 必填参数 (required) 是否缺失
    2. 已知参数的类型是否与 schema.properties 中声明的一致

    不阻断未知参数（兼容 MCP/FastMCP 的额外关键字参数）。
    """
    errors: List[str] = []
    if schema is None:
        return errors

    properties = schema.get("properties", {})
    required = schema.get("required", [])

    # 检查必填参数
    for req_param in required:
        if req_param not in arguments:
            errors.append(
                f"步骤 {step_idx}: 工具 '{tool_name}' 缺少必填参数 '{req_param}'"
            )

    # 检查已知参数类型
    for key, value in arguments.items():
        if key not in properties:
            # 未知参数仅记录 debug 日志，不阻断
            logger.debug(
                f"步骤 {step_idx}: 工具 '{tool_name}' 收到未知参数 '{key}'="
                f"{value!r}，跳过类型检查"
            )
            continue

        prop_schema = properties[key]
        expected_type = prop_schema.get("type")

        if expected_type and not _type_matches(value, expected_type):
            actual_type = type(value).__name__
            errors.append(
                f"步骤 {step_idx}: 工具 '{tool_name}' 参数 '{key}' 类型不匹配，"
                f"期望 {expected_type}，实际为 {actual_type} (值: {value!r})"
            )

    return errors


def validate_skill_steps(
    steps: List[Dict[str, Any]],
    mcp_tools: List[Any],
) -> None:
    """验证 Skill 解析出的步骤是否能在 MCP 服务器上正确执行.

    Args:
        steps: SOP 解析后的步骤列表，每个元素含 tool_name、arguments 等。
        mcp_tools: MCP ``session.list_tools()`` 返回的 Tool 对象列表。
                   期望每个对象至少有 ``name`` 和 ``inputSchema`` 属性。

    Raises:
        SkillValidationError: 收集所有错误后统一抛出，便于一次性修复。
    """
    # 构建 工具名 -> JSON Schema 映射
    schemas: Dict[str, Dict[str, Any]] = {}
    tool_names: set = set()

    for t in mcp_tools:
        name = getattr(t, "name", None)
        if not name:
            continue
        tool_names.add(name)
        schema = getattr(t, "inputSchema", None)
        if schema and isinstance(schema, dict):
            schemas[name] = schema

    errors: List[str] = []

    for i, step in enumerate(steps, 1):
        tool_name = step.get("tool_name")
        arguments = step.get("arguments", {})

        if not tool_name:
            errors.append(f"步骤 {i}: 未声明工具名")
            continue

        if tool_name not in tool_names:
            available = ", ".join(sorted(tool_names)) if tool_names else "(无)"
            errors.append(
                f"步骤 {i}: 工具 '{tool_name}' 不存在于 MCP Server 中。"
                f"可用工具: {available}"
            )
            continue

        schema = schemas.get(tool_name)
        step_errors = _validate_step_arguments(i, tool_name, arguments, schema)
        errors.extend(step_errors)

    if errors:
        header = f"Skill 验证失败，共 {len(errors)} 个问题:"
        detail = "\n".join(f"  - {e}" for e in errors)
        raise SkillValidationError(f"{header}\n{detail}")

    logger.info(f"Skill 验证通过: 共 {len(steps)} 个步骤，{len(tool_names)} 个可用工具")


def validate_skill_metadata_tools(
    metadata_tools: List[str],
    mcp_tools: List[Any],
) -> None:
    """验证 Skill frontmatter 中 ``tools:`` 声明的列表是否全部有效.

    Args:
        metadata_tools: frontmatter 中 ``tools`` 字段的值列表。
        mcp_tools: MCP ``session.list_tools()`` 返回的 Tool 对象列表。

    Raises:
        SkillValidationError: 存在未在 MCP 中注册的工具时抛出。
    """
    tool_names = {getattr(t, "name", None) for t in mcp_tools}
    tool_names.discard(None)

    errors: List[str] = []
    for declared in metadata_tools:
        if declared not in tool_names:
            errors.append(
                f"frontmatter 声明的工具 '{declared}' 不存在于 MCP Server 中"
            )

    if errors:
        available = ", ".join(sorted(tool_names)) if tool_names else "(无)"
        header = f"Skill metadata 验证失败，共 {len(errors)} 个问题:"
        detail = "\n".join(f"  - {e}" for e in errors)
        raise SkillValidationError(f"{header}\n{detail}\n可用工具: {available}")
