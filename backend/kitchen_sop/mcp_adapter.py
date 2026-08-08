"""langchain-mcp-adapters 的本地替代 shim.

langchain-mcp-adapters 目前钉死 mcp<2.0.0（v2 支持仍在跟进：
https://github.com/langchain-ai/langchain-mcp-adapters/issues/578）。
本项目升级到 MCP Python SDK v2（协议 2026-07-28）后，用本模块提供与
``load_mcp_tools`` 等价的接口。未来官方适配器支持 v2 后可直接替换回去。
"""

from typing import Any, Dict, List, Optional, Type

from langchain_core.tools import StructuredTool, ToolException
from pydantic import BaseModel, Field, create_model

_JSON_TYPE_MAP = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "array": list,
    "object": dict,
}


def _json_schema_to_pydantic(tool_name: str, schema: Dict[str, Any]) -> Type[BaseModel]:
    """把 MCP 工具的 input_schema（JSON Schema）转成 pydantic model."""
    fields: Dict[str, Any] = {}
    required = set(schema.get("required") or [])
    for prop, spec in (schema.get("properties") or {}).items():
        py_type = _JSON_TYPE_MAP.get(spec.get("type", "string"), Any)
        description = spec.get("description")
        if prop in required:
            fields[prop] = (py_type, Field(description=description))
        else:
            default = spec.get("default", None)
            fields[prop] = (
                Optional[py_type],
                Field(default=default, description=description),
            )
    return create_model(f"{tool_name}_args", **fields)


def _convert_mcp_tool(tool, client) -> StructuredTool:
    """把 MCP 原生 Tool 转成 LangChain StructuredTool（通过 client.call_tool 调用）."""
    args_schema = _json_schema_to_pydantic(tool.name, tool.input_schema or {})

    async def _call(**kwargs):
        result = await client.call_tool(tool.name, arguments=kwargs)
        text = "\n".join(
            block.text if hasattr(block, "text") else str(block)
            for block in result.content
        )
        if result.is_error:
            raise ToolException(text)
        return text

    return StructuredTool(
        name=tool.name,
        description=tool.description or "",
        args_schema=args_schema,
        coroutine=_call,
    )


async def load_mcp_tools_compat(client) -> List[StructuredTool]:
    """等价于 langchain-mcp-adapters 的 load_mcp_tools，面向 SDK v2 Client."""
    result = await client.list_tools()
    return [_convert_mcp_tool(tool, client) for tool in result.tools]
