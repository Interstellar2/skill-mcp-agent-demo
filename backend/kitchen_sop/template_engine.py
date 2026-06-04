"""SOP 模板渲染引擎：将 {{variable}} 占位符替换为实际值."""

import re
from pathlib import Path
from typing import Any, Dict, Optional


def render_sop(content: str, variables: Dict[str, Any]) -> str:
    """将 SOP Markdown 内容中的 {{var_name}} 替换为实际值.

    Args:
        content: 原始 SOP Markdown 内容.
        variables: 变量名到值的映射.

    Returns:
        替换后的 Markdown 内容.
    """

    def replacer(match: re.Match) -> str:
        key = match.group(1).strip()
        if key in variables:
            return str(variables[key])
        return match.group(0)

    return re.sub(r"\{\{\s*(\w+)\s*\}\}", replacer, content)


def render_template_file(template_path: Path, variables: Dict[str, Any]) -> str:
    """从文件加载模板并渲染变量占位符.

    Args:
        template_path: 模板文件路径（通常为 .md）.
        variables: 变量名到值的映射.

    Returns:
        渲染后的模板内容.
    """
    if not template_path.exists():
        return ""
    content = template_path.read_text(encoding="utf-8")
    return render_sop(content, variables)


def _resolve_variables(
    definitions: dict,
    overrides: Optional[dict] = None,
) -> Dict[str, Any]:
    """合并 Skill frontmatter 中的变量定义与 CLI 传入的覆盖值.

    Args:
        definitions: frontmatter 中 variables 字段的定义，如
            {"egg_count": {"type": "int", "default": 3, "description": "..."}}
        overrides: CLI 传入的变量值，如 {"egg_count": "5"}.

    Returns:
        合并后的变量字典，已按 type 做类型转换.
    """
    result: Dict[str, Any] = {}
    overrides = overrides or {}

    for key, meta in definitions.items():
        if isinstance(meta, dict):
            default = meta.get("default")
            var_type = meta.get("type", "string")
        else:
            # 简写形式: variables: {egg_count: 3}
            default = meta
            var_type = "string"

        raw_value = overrides.get(key, default)

        if raw_value is None:
            result[key] = None
            continue

        # 类型转换
        if var_type == "int":
            try:
                result[key] = int(raw_value)
            except (ValueError, TypeError):
                result[key] = raw_value
        elif var_type == "bool":
            if isinstance(raw_value, bool):
                result[key] = raw_value
            else:
                result[key] = str(raw_value).lower() in ("true", "1", "yes", "on")
        elif var_type == "float":
            try:
                result[key] = float(raw_value)
            except (ValueError, TypeError):
                result[key] = raw_value
        else:
            result[key] = raw_value

    # 将 overrides 中未在 definitions 中定义的键也加入（允许自由变量）
    for key, val in overrides.items():
        if key not in result:
            result[key] = val

    return result
