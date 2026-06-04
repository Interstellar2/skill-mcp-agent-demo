"""项目配置管理：环境变量加载与常量定义."""

import os
from pathlib import Path

from dotenv import load_dotenv

# 项目根目录（backend/kitchen_sop/config.py → project root）
PROJECT_ROOT = Path(__file__).parent.parent.parent


def load_env():
    """加载项目根目录的 .env 文件，若不存在则尝试加载系统环境变量."""
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=True)
    else:
        load_dotenv(override=True)


# 默认配置
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_SKILL = "tomato_egg"
SKILLS_DIR = PROJECT_ROOT / "skills"
LOGS_DIR = PROJECT_ROOT / "logs"
RUNS_DIR = PROJECT_ROOT / "runs"
