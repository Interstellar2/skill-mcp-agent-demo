"""Skill 解析与加载领域包."""

from .generator import (
    generate_skill_draft,
    preview_skill_draft,
    save_skill,
    SkillGenerationError,
)
from .manager import Skill, SkillsManager
from .memory import SkillMemory
from .parser import parse_gotchas, parse_sop_steps
from .reference import ReferenceLoader
from .script import ScriptContext, ScriptRunner
from .template import render_sop, render_template_file, _resolve_variables
from .validator import (
    SkillValidationError,
    validate_skill_metadata_tools,
    validate_skill_steps,
)

__all__ = [
    "Skill",
    "SkillsManager",
    "SkillMemory",
    "parse_sop_steps",
    "parse_gotchas",
    "ReferenceLoader",
    "ScriptContext",
    "ScriptRunner",
    "render_sop",
    "render_template_file",
    "_resolve_variables",
    "SkillValidationError",
    "validate_skill_metadata_tools",
    "validate_skill_steps",
    "generate_skill_draft",
    "preview_skill_draft",
    "save_skill",
    "SkillGenerationError",
]
