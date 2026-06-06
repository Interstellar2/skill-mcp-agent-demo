"""SOP 模板渲染与变量处理."""

import re
from pathlib import Path
from typing import Any, Dict, Optional


def _resolve_variables(
    declared: Dict[str, Any], overrides: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """合并声明的变量默认值与用户覆盖值."""
    overrides = overrides or {}
    merged: Dict[str, Any] = {}
    for key, info in declared.items():
        if isinstance(info, dict):
            default = info.get("default")
            merged[key] = overrides.get(key, default)
        else:
            merged[key] = overrides.get(key, info)
    # 追加 overrides 中不在 declared 的变量
    for key, value in overrides.items():
        if key not in merged:
            merged[key] = value
    return merged


def render_sop(content: str, variables: Optional[Dict[str, Any]] = None) -> str:
    """渲染 SOP 模板，支持 {{var}} 和 <!--HIDDEN--><!--/HIDDEN--> 语法."""
    variables = variables or {}
    # 处理隐藏块
    content = re.sub(
        r"<!--\s*HIDDEN\s*-->(.*?)<!--\s*/HIDDEN\s*-->",
        "",
        content,
        flags=re.DOTALL,
    )
    # 处理变量插值
    for key, value in variables.items():
        content = content.replace(f"{{{{{key}}}}}", str(value))
    return content


def render_template_file(template_path: Path, variables: Dict[str, Any]) -> Optional[str]:
    """渲染模板文件."""
    if not template_path.exists():
        return None
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()
    return render_sop(content, variables)
