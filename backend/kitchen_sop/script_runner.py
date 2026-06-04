"""Script execution engine for pre/post hooks."""

import logging
import runpy
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger("kitchen_agent")


class ScriptContext:
    """传递给 Skill 脚本执行的上下文对象."""

    def __init__(self, skill_name: str, variables: Dict[str, Any]):
        self.skill_name = skill_name
        self.variables = variables
        self.output = ""

    def get(self, key: str, default: Any = None) -> Any:
        return self.variables.get(key, default)


class ScriptRunner:
    """执行 Skill 目录 scripts/ 下的 Python 脚本."""

    def run(self, script_path: Path, context: ScriptContext) -> ScriptContext:
        if not script_path.exists():
            return context

        logger.info(f"🔧 执行脚本: {script_path.name}")
        try:
            module = runpy.run_path(
                str(script_path),
                init_globals={"context": context},
            )
            # 脚本可以通过 return_value 变量回传结果
            if "return_value" in module:
                context.output = str(module["return_value"])
        except Exception as e:
            logger.error(f"脚本执行失败: {e}")
            raise

        return context
