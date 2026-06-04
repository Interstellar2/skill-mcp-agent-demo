"""统一日志配置，供 agent 侧和 MCP 服务端共用."""

import logging
import sys
from datetime import datetime
from pathlib import Path


def setup_logging(
    name: str,
    log_dir: str = "logs",
    log_level: str = "INFO",
    console_level: str = "INFO",
    file_level: str = "DEBUG",
    console_stream=None,
) -> logging.Logger:
    """配置双通道日志：同时输出到终端和本地文件.

    Args:
        name: Logger 名称.
        log_dir: 日志文件存放目录.
        log_level: Logger 全局级别.
        console_level: 终端输出级别.
        file_level: 文件输出级别.
        console_stream: 终端输出流，默认 stdout.

    Returns:
        配置好的 Logger 实例.
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # 避免重复添加 handler
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 终端输出
    console_handler = logging.StreamHandler(console_stream or sys.stdout)
    console_handler.setLevel(getattr(logging, console_level.upper(), logging.INFO))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件输出
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now().strftime("%Y-%m-%d")
    file_handler = logging.FileHandler(
        filename=log_path / f"{date_str}.log",
        encoding="utf-8",
    )
    file_handler.setLevel(getattr(logging, file_level.upper(), logging.DEBUG))
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
