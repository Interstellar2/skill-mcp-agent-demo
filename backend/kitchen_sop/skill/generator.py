"""Skill 生成器：LLM 草稿生成、预览解析、安全落盘."""

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from langchain_openai import ChatOpenAI

from ..config import SKILLS_DIR
from .manager import SkillsManager
from .parser import parse_sop_steps
from .template import render_sop
from .validator import (
    SkillValidationError,
    validate_skill_metadata_tools,
    validate_skill_steps,
)


class SkillGenerationError(Exception):
    """Skill 生成过程中出现的错误."""

    pass


_SKILL_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


def _load_example_skill_markdown() -> str:
    """加载 tomato_egg SKILL.md 作为完整示例."""
    example_path = SKILLS_DIR / "tomato_egg" / "SKILL.md"
    if example_path.exists():
        return example_path.read_text(encoding="utf-8")
    return ""


def _format_tool_schema(tool: Any) -> Dict[str, Any]:
    """将 MCP 工具对象序列化为可嵌入 prompt 的字典."""
    schema = getattr(tool, "inputSchema", None) or {}
    if not isinstance(schema, dict):
        try:
            schema = json.loads(schema)
        except Exception:
            schema = {}
    return {
        "name": getattr(tool, "name", ""),
        "description": getattr(tool, "description", ""),
        "inputSchema": schema,
    }


def _build_system_prompt(mcp_tools: Optional[List[Any]] = None) -> str:
    """构建生成 SKILL.md 的 system prompt."""
    example = _load_example_skill_markdown()
    tools_text = ""
    if mcp_tools:
        tools_text = "\n".join(
            f"- `{t['name']}`: {t['description']}\n  schema: {json.dumps(t['inputSchema'], ensure_ascii=False)}"
            for t in [_format_tool_schema(tool) for tool in mcp_tools]
        )

    return f"""你是一位专业的中餐 SOP 设计助手。你的任务是根据用户的自然语言描述，生成一份符合项目规范的 SKILL.md 文件。

## 输出格式要求

文件必须包含 YAML frontmatter（位于 `---` 之间）和 Markdown body 两部分。

frontmatter 支持以下字段：
- `name`: skill 的英文标识符，只能使用字母、数字、下划线和短横线。
- `description`: 触发条件，≤250 字符，例如："当用户要做番茄炒蛋、需要处理番茄和鸡蛋食材时使用"。
- `variables`: 可选，定义执行时可替换的变量及其默认值、类型、描述。
- `tools`: 该 skill 会用到的 MCP 工具名列表，必须从下方“可用工具”中选择。
- `human_in_the_loop`: 可选，需要人工确认的步骤列表，每项包含 `step` 和 `prompt`。
- `scripts`: 可选，预执行脚本路径映射。
- `templates`: 可选，模板文件路径映射。
- `references`: 可选，要注入 prompt 的参考文件名列表（这些文件应放在 `references/` 目录下）。
- `hooks`: 可选，skill 级临时 hook 列表，当前支持 `careful`（安全阻断）和 `freeze`（只读）。

Markdown body 结构：
1. 一个一级标题 `# <菜名> SOP`。
2. `## 食材准备` 段落，可列出食材和变量（使用 `{{{{variable_name}}}}`）。
3. `## 操作步骤`，每个步骤使用 `### 步骤 N: <标题>`。
4. 每个步骤内部必须包含：
   - `**工具**: `<tool_name>``（工具名必须来自可用工具列表）。
   - 可选并行标记：`[parallel-group: xxx]` 或 `[depends-on: xxx]`，紧跟在工具声明行的末尾。
   - `**参数**:` 后跟 `- key: value` 列表，参数名必须符合工具 schema 的 `properties`，必填参数必须在 schema 的 `required` 中提供。
5. `## 坑点清单` 段落，列出 2-5 条该 skill 独有的、模型推断不出来的坑。
6. `## 成功标准` 段落，列出成功标准。

## 可用工具

{tools_text or "（暂无可用工具，请仅使用 markdown 描述）"}

## 重要约束

1. 只输出 SKILL.md 内容，不要输出任何解释、代码块标记或额外文字。
2. 工具名必须从“可用工具”列表中精确选择，参数必须符合对应工具的 inputSchema。
3. 优先使用可用的厨房类工具（如 cut_ingredient、crack_egg、heat_pan、stir_fry、season、plate 等）来构建步骤。
4. 不要编造不存在的工具或参数。
5. 步骤描述要简洁、可操作，参数值使用中文或简单英文。
6. `description` 必须写成触发条件，≤250 字符，例如："当用户要做番茄炒蛋、需要处理番茄和鸡蛋食材时使用。"
7. Markdown body 必须包含 `## 坑点清单`，列出 2-5 条该 skill 独有的、模型推断不出来的坑。
8. 详细参考资料不要 inline，放到 `references/` 目录，并在 frontmatter `references:` 中声明。

## 完整示例

{example}
"""


def _parse_frontmatter(markdown: str) -> Optional[Dict[str, Any]]:
    """解析 YAML frontmatter，返回 metadata 或 None."""
    if not markdown.startswith("---"):
        return None
    parts = markdown.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        return yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return None


def _extract_sop_body(markdown: str) -> str:
    """去掉 frontmatter，返回 Markdown body."""
    if not markdown.startswith("---"):
        return markdown
    parts = markdown.split("---", 2)
    if len(parts) < 3:
        return markdown
    return parts[2].strip()


async def generate_skill_draft(
    prompt: str,
    model: Optional[str] = None,
    mcp_tools: Optional[List[Any]] = None,
) -> str:
    """使用 LLM 根据自然语言描述生成 SKILL.md 草稿.

    Args:
        prompt: 用户的自然语言描述。
        model: 指定模型名称，默认从环境变量 MODEL 或 gpt-4o-mini 读取。
        mcp_tools: 可选的 MCP 工具列表，用于约束生成内容。

    Returns:
        生成的 SKILL.md 字符串。

    Raises:
        SkillGenerationError: 缺少 API Key 或 LLM 调用失败。
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL")
    model = model or os.environ.get("MODEL", "gpt-4o-mini")

    if not api_key:
        raise SkillGenerationError("未设置 OPENAI_API_KEY")

    llm_kwargs: Dict[str, Any] = {"model": model, "temperature": 0.2, "api_key": api_key}
    if base_url:
        llm_kwargs["base_url"] = base_url

    try:
        llm = ChatOpenAI(**llm_kwargs)
        system_prompt = _build_system_prompt(mcp_tools)
        messages = [
            ("system", system_prompt),
            ("user", prompt),
        ]
        response = await llm.ainvoke(messages)
        content = response.content if hasattr(response, "content") else str(response)
    except Exception as e:
        raise SkillGenerationError(f"LLM 生成失败: {e}") from e

    content = content.strip()
    # 去除可能的 markdown 代码块包裹
    if content.startswith("```"):
        lines = content.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        content = "\n".join(lines).strip()
    return content


def preview_skill_draft(
    markdown: str,
    sm: Optional[SkillsManager] = None,
    mcp_tools: Optional[List[Any]] = None,
) -> Dict[str, Any]:
    """预览 SKILL.md 草稿，解析元数据、步骤并执行前置校验.

    Args:
        markdown: SKILL.md 内容。
        sm: 可选的 SkillsManager，用于解析子流程。
        mcp_tools: 可选的 MCP 工具列表，用于校验工具存在性和参数 schema。

    Returns:
        包含 metadata、steps、errors、step_errors、valid 的字典。
    """
    result: Dict[str, Any] = {
        "metadata": {},
        "steps": [],
        "errors": [],
        "step_errors": [],
        "valid": False,
    }

    metadata = _parse_frontmatter(markdown)
    if metadata is None:
        result["errors"].append("无法解析 YAML frontmatter")
        return result
    result["metadata"] = metadata

    body = _extract_sop_body(markdown)

    # 解析步骤
    try:
        rendered = render_sop(body, {})
        steps = parse_sop_steps(rendered, sm=sm, variables={})
        result["steps"] = steps
    except ValueError as e:
        result["errors"].append(f"步骤解析失败: {e}")
        return result
    except Exception as e:
        result["errors"].append(f"步骤解析异常: {e}")
        return result

    # 若未提供 mcp_tools，尝试从 MCP 连接池获取
    tools_for_validation = mcp_tools
    if tools_for_validation is None:
        try:
            from ..mcp_pool import get_mcp_pool

            pool = get_mcp_pool()
            if pool and pool.session:
                tools_result = pool.session.list_tools()
                if hasattr(tools_result, "tools"):
                    tools_for_validation = tools_result.tools
        except Exception:
            tools_for_validation = None

    if tools_for_validation is None:
        # 无法获取工具列表时，仅做解析级校验
        result["valid"] = not result["errors"] and not result["step_errors"]
        return result

    # 校验 metadata 中声明的工具
    try:
        declared = metadata.get("tools", [])
        if declared:
            validate_skill_metadata_tools(declared, tools_for_validation)
    except SkillValidationError as e:
        result["errors"].extend(str(e).splitlines())

    # 校验步骤中的工具调用
    try:
        validate_skill_steps(steps, tools_for_validation)
    except SkillValidationError as e:
        for line in str(e).splitlines():
            line = line.strip()
            if line.startswith("-"):
                line = line[1:].strip()
            if not line or line.startswith("Skill"):
                continue
            m = re.match(r"步骤\s+(\d+):\s*(.*)", line)
            if m:
                result["step_errors"].append(
                    {"step_index": int(m.group(1)), "message": m.group(2)}
                )
            else:
                result["errors"].append(line)

    result["valid"] = not result["errors"] and not result["step_errors"]
    return result


def save_skill(
    name: str,
    markdown: str,
    skills_dir: Optional[Path] = None,
    overwrite: bool = False,
) -> Path:
    """将 SKILL.md 草稿安全落盘.

    Args:
        name: skill 目录名，必须匹配 `^[a-zA-Z0-9_-]+$`。
        markdown: 完整的 SKILL.md 内容。
        skills_dir: skill 根目录，默认使用项目配置。
        overwrite: 是否覆盖已存在的 skill 目录。

    Returns:
        写入的 SKILL.md 文件路径。

    Raises:
        SkillGenerationError: name 非法或落盘失败。
    """
    if not name or not _SKILL_NAME_RE.match(name):
        raise SkillGenerationError(
            f"非法的 skill 名称: {name}（只允许字母、数字、下划线和短横线）"
        )

    target_dir = Path(skills_dir) if skills_dir else SKILLS_DIR
    skill_dir = target_dir / name
    skill_file = skill_dir / "SKILL.md"

    if skill_dir.exists() and not overwrite:
        raise SkillGenerationError(
            f"Skill '{name}' 已存在，设置 overwrite=True 可覆盖"
        )

    try:
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_file.write_text(markdown, encoding="utf-8")
    except OSError as e:
        raise SkillGenerationError(f"保存 skill 失败: {e}") from e

    return skill_file
