"""MCP 单例连接池：在 FastAPI lifespan 中启动，所有 executor 共享一个 MCP 连接.

基于 MCP Python SDK v2 的 ``Client``（协议 2026-07-28，dual-era 自动协商）。
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client

from .mcp_adapter import load_mcp_tools_compat

logger = logging.getLogger("kitchen_agent")

_DEFAULT_MCP_SERVER = str(Path(__file__).parent.parent / "mcp_server.py")


class MCPConnectionPool:
    """全局单例 MCP 连接池，支持 async start/stop 和带锁的 call_tool."""

    _instance: Optional["MCPConnectionPool"] = None
    _lock = asyncio.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, server_script: str = _DEFAULT_MCP_SERVER, mode: str = "auto"):
        if self._initialized:
            return
        self.server_script = server_script
        self.mode = mode
        self._tool_lock = asyncio.Lock()
        self._client: Optional[Client] = None
        self._tools: Optional[list] = None
        self._mcp_tools: Optional[list] = None
        self._initialized = True

    async def start(self):
        """启动 MCP 连接（幂等）."""
        async with self._lock:
            if self._client is not None:
                return
            server_params = StdioServerParameters(
                command="python",
                args=[self.server_script],
                env=None,
            )
            client = Client(stdio_client(server_params), mode=self.mode)
            await client.__aenter__()
            try:
                self._tools = await load_mcp_tools_compat(client)
                # 同时缓存 MCP 原生工具列表（含 JSON Schema），供验证器使用
                tools_result = await client.list_tools()
                self._mcp_tools = tools_result.tools
            except Exception:
                await client.__aexit__(None, None, None)
                raise
            self._client = client
            logger.info(
                f"MCPConnectionPool started with {len(self._tools)} tools "
                f"({len(self._mcp_tools)} raw MCP tools, "
                f"protocol {client.protocol_version})"
            )

    async def stop(self):
        """关闭 MCP 连接."""
        async with self._lock:
            if self._client is not None:
                try:
                    await self._client.__aexit__(None, None, None)
                except Exception:
                    pass
                self._client = None
            self._tools = None
            self._mcp_tools = None
            logger.info("MCPConnectionPool stopped")

    @property
    def session(self) -> Client:
        """返回 v2 Client（call_tool/list_tools 接口与原 ClientSession 兼容）."""
        if self._client is None:
            raise RuntimeError("MCPConnectionPool not started")
        return self._client

    @property
    def tools(self) -> list:
        if self._tools is None:
            raise RuntimeError("MCPConnectionPool not started")
        return self._tools

    @property
    def mcp_tools(self) -> list:
        """返回 MCP 原生 Tool 对象列表（含 input_schema），供验证器使用."""
        if self._mcp_tools is None:
            raise RuntimeError("MCPConnectionPool not started")
        return self._mcp_tools

    async def call_tool(self, tool_name: str, arguments: dict):
        """带锁的 call_tool，保证 JSON-RPC over stdio 串行化."""
        async with self._tool_lock:
            return await self._client.call_tool(tool_name, arguments=arguments)

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()
        return False


def get_mcp_pool() -> MCPConnectionPool:
    """获取全局 MCP 连接池实例."""
    return MCPConnectionPool()
