"""MCP 单例连接池：在 FastAPI lifespan 中启动，所有 executor 共享一个 MCP session."""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools

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

    def __init__(self, server_script: str = _DEFAULT_MCP_SERVER):
        if self._initialized:
            return
        self.server_script = server_script
        self._tool_lock = asyncio.Lock()
        self._session: Optional[ClientSession] = None
        self._tools: Optional[list] = None
        self._read = None
        self._write = None
        self._stdio_ctx = None
        self._session_ctx = None
        self._initialized = True

    async def start(self):
        """启动 MCP 连接（幂等）."""
        async with self._lock:
            if self._session is not None:
                return
            server_params = StdioServerParameters(
                command="python",
                args=[self.server_script],
                env=None,
            )
            self._stdio_ctx = stdio_client(server_params)
            self._read, self._write = await self._stdio_ctx.__aenter__()
            self._session_ctx = ClientSession(self._read, self._write)
            self._session = await self._session_ctx.__aenter__()
            await self._session.initialize()
            self._tools = await load_mcp_tools(self._session)
            logger.info(f"MCPConnectionPool started with {len(self._tools)} tools")

    async def stop(self):
        """关闭 MCP 连接."""
        async with self._lock:
            if self._session_ctx is not None:
                try:
                    await self._session_ctx.__aexit__(None, None, None)
                except Exception:
                    pass
                self._session_ctx = None
            if self._stdio_ctx is not None:
                try:
                    await self._stdio_ctx.__aexit__(None, None, None)
                except Exception:
                    pass
                self._stdio_ctx = None
            self._session = None
            self._tools = None
            logger.info("MCPConnectionPool stopped")

    @property
    def session(self) -> ClientSession:
        if self._session is None:
            raise RuntimeError("MCPConnectionPool not started")
        return self._session

    @property
    def tools(self) -> list:
        if self._tools is None:
            raise RuntimeError("MCPConnectionPool not started")
        return self._tools

    async def call_tool(self, tool_name: str, arguments: dict):
        """带锁的 call_tool，保证 JSON-RPC over stdio 串行化."""
        async with self._tool_lock:
            return await self._session.call_tool(tool_name, arguments=arguments)

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()
        return False


def get_mcp_pool() -> MCPConnectionPool:
    """获取全局 MCP 连接池实例."""
    return MCPConnectionPool()
