"""
Kitchen MCP Server - 厨房工具 MCP 服务器（MOCK）

提供一系列模拟厨房操作的工具，用于番茄炒鸡蛋 SOP 的演示。
通过 stdio 传输 JSON-RPC 消息与客户端通信。

日志输出:
- stderr: 终端可见（不影响 stdio JSON-RPC 通信）
- logs/mcp_server_YYYY-MM-DD.log: 本地持久化

运行方式: python mcp_server.py
"""

import asyncio
import functools
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from mcp.server.fastmcp import FastMCP


# ============ 日志配置 ============


def _setup_mcp_logging() -> logging.Logger:
    """配置 MCP 服务器专属日志，输出到 stderr（不占用 stdout）和本地文件。"""
    logger = logging.getLogger("mcp_server")
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # stderr → 终端可见，不干扰 stdio
    sh = logging.StreamHandler(sys.stderr)
    sh.setLevel(logging.INFO)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    # 文件 → 持久化
    PROJECT_ROOT = Path(__file__).parent.parent
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(
        log_dir / f"mcp_server_{datetime.now():%Y-%m-%d}.log",
        encoding="utf-8",
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger


logger = _setup_mcp_logging()


# ============ 工具调用日志装饰器 ============


def log_tool_call(func):
    """
    自动记录工具调用的装饰器。

    记录内容:
    - 调用前: 工具名 + 参数
    - 调用后: 返回值
    - 异常时: 错误信息
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        tool_name = func.__name__
        # 过滤掉 mcp 内部可能注入的 _meta 等参数
        call_args = {k: v for k, v in kwargs.items() if not k.startswith("_")}
        logger.info(
            f"[TOOL CALL] {tool_name} | args={json.dumps(call_args, ensure_ascii=False)}"
        )
        try:
            result = func(*args, **kwargs)
            logger.info(f"[TOOL DONE] {tool_name} | result={result}")
            return result
        except Exception as e:
            logger.error(f"[TOOL FAIL] {tool_name} | error={e}")
            raise

    return wrapper


# ============ MCP 服务器实例 ============

mcp = FastMCP("kitchen")


# ============ 工具定义 ============


@mcp.tool()
@log_tool_call
def cut_ingredient(ingredient: str, method: str) -> str:
    """
    切割食材。

    Args:
        ingredient: 食材名称，如 "番茄", "土豆", "洋葱"
        method: 切割方式，如 "切块", "切片", "切丝", "切丁", "切末"

    Returns:
        切割完成的状态描述
    """
    return f"✅ [{ingredient}] 已按 [{method}] 方式处理完毕，备用。"


@mcp.tool()
@log_tool_call
def crack_egg(count: int, mix: bool = True) -> str:
    """
    打蛋并可选搅拌均匀。

    Args:
        count: 鸡蛋数量
        mix: 是否搅拌，默认为 True

    Returns:
        打蛋完成的状态描述
    """
    action = "并搅拌均匀" if mix else ""
    return f"✅ 已将 {count} 个鸡蛋打入碗中{action}，蛋液备用。"


@mcp.tool()
@log_tool_call
def heat_pan(temperature: str, duration: int) -> str:
    """
    热锅并加入食用油。

    Args:
        temperature: 火力档位，如 "小火", "中火", "大火", "中大火"
        duration: 预热时间（秒）

    Returns:
        热锅完成的状态描述
    """
    return f"✅ 锅已用 [{temperature}] 预热 {duration} 秒，倒入适量食用油，油温适中。"


@mcp.tool()
@log_tool_call
def stir_fry(ingredient: str, duration: int, technique: str) -> str:
    """
    翻炒食材。

    Args:
        ingredient: 要翻炒的食材
        duration: 翻炒时间（秒）
        technique: 翻炒技法，如 "滑炒", "煸炒", "翻炒均匀", "大火快炒"

    Returns:
        翻炒完成的状态描述
    """
    return f"✅ 用 [{technique}] 技法翻炒 [{ingredient}] {duration} 秒，完成。"


@mcp.tool()
@log_tool_call
def season(
    salt: str = "", sugar: str = "", soy_sauce: str = "", other: str = ""
) -> str:
    """
    给菜肴调味。

    Args:
        salt: 盐的用量，如 "1小勺"
        sugar: 糖的用量，如 "1/2小勺"
        soy_sauce: 酱油用量
        other: 其他调味料

    Returns:
        调味完成的状态描述
    """
    added = []
    if salt:
        added.append(f"盐 {salt}")
    if sugar:
        added.append(f"糖 {sugar}")
    if soy_sauce:
        added.append(f"酱油 {soy_sauce}")
    if other:
        added.append(other)

    if not added:
        return "⚠️ 没有添加任何调味料。"

    return f"✅ 已加入调味料: {', '.join(added)}，味道均匀融合。"


@mcp.tool()
@log_tool_call
def plate(garnish: str = "") -> str:
    """
    将菜肴装盘，可撒点缀。

    Args:
        garnish: 点缀食材，如 "葱花", "香菜", "白芝麻"

    Returns:
        装盘完成的状态描述
    """
    if garnish:
        return f"✅ 菜肴已盛入盘中，撒上 [{garnish}] 点缀，色香味俱全！"
    return "✅ 菜肴已盛入盘中，可以上桌了！"


# ============ 服务器入口 ============

if __name__ == "__main__":
    logger.info("MCP Kitchen Server 启动，等待客户端连接...")
    asyncio.run(mcp.run_stdio_async())
