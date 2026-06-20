"""Skill 预执行/后执行脚本运行器."""

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional


@dataclass
class ScriptContext:
    """脚本执行上下文."""

    skill_name: str
    variables: Dict[str, any] = field(default_factory=dict)
    output: str = ""
    returncode: int = 0
    data_dir: Optional[Path] = None


class ScriptRunner:
    """运行 Skill 声明的 pre/post 脚本."""

    def run(self, script_path: Path, ctx: ScriptContext) -> None:
        """执行脚本并将 stdout 写入 ctx.output."""
        if not script_path.exists():
            return

        env = os.environ.copy()
        env["SKILL_NAME"] = ctx.skill_name
        if ctx.data_dir is not None:
            env["KITCHEN_SKILL_DATA_DIR"] = str(ctx.data_dir)
        for key, value in ctx.variables.items():
            env[f"SKILL_VAR_{key}"] = str(value)

        try:
            result = subprocess.run(
                [str(script_path)],
                capture_output=True,
                text=True,
                env=env,
                check=False,
                timeout=30,
            )
            ctx.output = result.stdout.strip()
            ctx.returncode = result.returncode
        except Exception as e:
            ctx.output = f"脚本执行失败: {e}"
            ctx.returncode = -1
