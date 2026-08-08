"""MCP 客户端连接管理（MCP Python SDK v2 / 协议 2026-07-28）.

SDK v2 用 ``Client`` 取代了 v1 的 ``ClientSession + initialize()`` 三层嵌套：
- mode="auto"（默认）：先 ``server/discover`` 探测，老 server 自动回退 initialize 握手
- mode="legacy"：强制旧时代 initialize 握手（协议 2025-11-25）
- mode="2026-07-28"：钉死新版无状态协议，零协商流量
"""

from contextlib import asynccontextmanager
from pathlib import Path

from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client

from .mcp_adapter import load_mcp_tools_compat


# 默认指向 backend/mcp_server.py
_DEFAULT_MCP_SERVER = str(Path(__file__).parent.parent / "mcp_server.py")


@asynccontextmanager
async def get_mcp_tools(server_script: str = _DEFAULT_MCP_SERVER, mode: str = "auto"):
    """启动 MCP 服务器并加载工具，作为异步上下文管理器使用.

    Args:
        server_script: MCP server 脚本路径。
        mode: 协议协商模式（"auto" / "legacy" / "2026-07-28"）。

    Usage:
        async with get_mcp_tools() as (tools, client):
            # 使用 tools
    """
    server_params = StdioServerParameters(
        command="python",
        args=[server_script],
        env=None,
    )

    async with Client(stdio_client(server_params), mode=mode) as client:
        tools = await load_mcp_tools_compat(client)
        yield tools, client
