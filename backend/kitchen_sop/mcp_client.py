"""MCP 客户端连接管理."""

from contextlib import asynccontextmanager
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools


# 默认指向 backend/mcp_server.py
_DEFAULT_MCP_SERVER = str(Path(__file__).parent.parent / "mcp_server.py")


@asynccontextmanager
async def get_mcp_tools(server_script: str = _DEFAULT_MCP_SERVER):
    """启动 MCP 服务器并加载工具，作为异步上下文管理器使用.

    Usage:
        async with get_mcp_tools() as (tools, session):
            # 使用 tools
    """
    server_params = StdioServerParameters(
        command="python",
        args=[server_script],
        env=None,
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await load_mcp_tools(session)
            yield tools, session
