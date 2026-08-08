#!/usr/bin/env python
"""MCP 协议前后版本对比演示：2025-11-25（握手时代） vs 2026-07-28（无状态时代）.

本项目的 backend/mcp_server.py 基于 MCP Python SDK v2，是一个 dual-era server：
同一个进程、同一个 stdio 端点，既能应答旧时代的 initialize 握手，
也能应答新时代的 server/discover 无状态请求，无需任何配置。

本脚本直接以裸 JSON-RPC over stdio 分别用两个时代的"方言"与同一个 server
对话，逐条打印 wire 消息，直观展示协议差异。

运行方式: python scripts/demo_protocol_eras.py
"""

import asyncio
import json
import unicodedata
from pathlib import Path

SERVER_SCRIPT = str(Path(__file__).parent.parent / "backend" / "mcp_server.py")

# 2026-07-28：每个请求通过 _meta envelope 自描述（无握手、无会话）
MODERN_META = {
    "_meta": {
        "io.modelcontextprotocol/protocolVersion": "2026-07-28",
        "io.modelcontextprotocol/clientInfo": {"name": "demo-modern-client", "version": "1.0"},
        "io.modelcontextprotocol/clientCapabilities": {},
    }
}


def _pp(obj, max_len=560) -> str:
    """紧凑打印 JSON，过长截断。"""
    text = json.dumps(obj, ensure_ascii=False)
    return text if len(text) <= max_len else text[:max_len] + " …"


async def _rpc(proc, msg, label, show_response=True):
    """发送一条 JSON-RPC 消息并读取响应（notification 无响应）。"""
    print(f"  >>> {label}")
    print(f"      {_pp(msg)}")
    proc.stdin.write((json.dumps(msg) + "\n").encode())
    await proc.stdin.drain()
    if msg.get("id") is None:  # notification，无响应
        print("      (notification，无响应)")
        return None
    line = await asyncio.wait_for(proc.stdout.readline(), timeout=15)
    resp = json.loads(line)
    if show_response:
        print(f"  <<< {_pp(resp)}")
    return resp


async def _spawn_server():
    return await asyncio.create_subprocess_exec(
        "python", SERVER_SCRIPT,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )


async def demo_legacy_era():
    """旧时代（2025-11-25 及之前）：initialize 三次握手 + 会话式请求。"""
    print("=" * 72)
    print("【旧时代】协议 2025-11-25：initialize / initialized 握手")
    print("=" * 72)
    proc = await _spawn_server()
    try:
        resp = await _rpc(proc, {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "demo-legacy-client", "version": "1.0"},
            },
        }, "initialize（协商协议版本、交换能力）")
        negotiated = resp["result"]["protocolVersion"]

        await _rpc(proc, {
            "jsonrpc": "2.0", "method": "notifications/initialized",
        }, "notifications/initialized（握手第三步）")

        resp = await _rpc(proc, {
            "jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {},
        }, "tools/list（握手完成后才能调用）", show_response=False)
        result = resp["result"]
        print(f"  <<< tools: {[t['name'] for t in result['tools']]}")
        print(f"      结果字段: {sorted(result.keys())}（注意：无 resultType / ttlMs）")
        return negotiated
    finally:
        proc.kill()
        await proc.wait()


async def demo_modern_era():
    """新时代（2026-07-28）：无握手，server/discover 一次探测 + _meta 自描述请求。"""
    print()
    print("=" * 72)
    print("【新时代】协议 2026-07-28：无握手，server/discover + 每请求 _meta envelope")
    print("=" * 72)
    proc = await _spawn_server()
    try:
        resp = await _rpc(proc, {
            "jsonrpc": "2.0", "id": 1, "method": "server/discover",
            "params": dict(MODERN_META),
        }, "server/discover（首条消息即业务请求，无需握手）")
        supported = resp["result"]["supportedVersions"]

        resp = await _rpc(proc, {
            "jsonrpc": "2.0", "id": 2, "method": "tools/list",
            "params": dict(MODERN_META),
        }, "tools/list（_meta 携带 protocolVersion/clientInfo/capabilities）", show_response=False)
        result = resp["result"]
        print(f"  <<< tools: {[t['name'] for t in result['tools']]}")
        extras = {k: v for k, v in result.items() if k != "tools"}
        print(f"      结果字段: {_pp(extras)}")
        print(f"      （ttlMs=60000 来自 server 的 cache_hints 配置）")

        await _rpc(proc, {
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "crack_egg", "arguments": {"count": 2}, **MODERN_META},
        }, "tools/call crack_egg（任意请求都可直接发起，无会话前置）")
        return supported
    finally:
        proc.kill()
        await proc.wait()


def _dw_pad(text: str, width: int) -> str:
    """按显示宽度补齐（CJK 字符占 2 列）。"""
    dw = sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text)
    return text + " " * max(0, width - dw)


def print_comparison(negotiated, supported):
    print()
    print("=" * 72)
    print("前后版本对照")
    print("=" * 72)
    rows = [
        ("建立连接", "initialize + initialized 三次握手", "无握手，首条即可发业务请求"),
        ("版本协商", "握手时协商，绑定整个会话", "每请求 _meta 自描述；server/discover 预探测"),
        ("会话状态", "协议级会话（HTTP 下 Mcp-Session-Id）", "无协议会话，跨调用状态用显式 handle"),
        ("Server 身份", "initialize 响应的 serverInfo", "每个结果 _meta 的 serverInfo"),
        ("结果元数据", "无", "resultType 必填；list 结果带 ttlMs/cacheScope"),
        ("日志/Roots/Sampling", "协议内能力", "已 deprecated（建议 stderr / OTel / 工具参数）"),
    ]
    w1, w2 = 20, 44
    print(f"  {_dw_pad('', w1)}{_dw_pad('2025-11-25（旧）', w2)}2026-07-28（新）")
    print(f"  {'-' * w1}{'-' * w2}{'-' * 30}")
    for name, old, new in rows:
        print(f"  {_dw_pad(name, w1)}{_dw_pad(old, w2)}{new}")
    print()
    print(f"  本次实测：旧时代握手协商到 {negotiated}；新时代 server 声明支持 {supported}")
    print("  同一个 server 进程同时讲两种时代（dual-era），由 SDK v2 自动分流。")


async def main():
    if not Path(SERVER_SCRIPT).exists():
        raise SystemExit(f"找不到 server 脚本: {SERVER_SCRIPT}")
    negotiated = await demo_legacy_era()
    supported = await demo_modern_era()
    print_comparison(negotiated, supported)


if __name__ == "__main__":
    asyncio.run(main())
