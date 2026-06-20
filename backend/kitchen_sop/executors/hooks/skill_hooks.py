"""Skill 级临时 hook：在执行期间注入，结束后自动卸载."""

import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from .base import StepHook


logger = logging.getLogger("kitchen_agent")


def build_skill_hooks(metadata: Dict[str, Any]) -> List[StepHook]:
    """根据 frontmatter `hooks` 列表构建 skill 级 hook 实例.

    Args:
        metadata: Skill frontmatter 元数据。

    Returns:
        StepHook 实例列表。
    """
    hooks: List[StepHook] = []
    hook_names = metadata.get("hooks", []) if metadata else []
    for name in hook_names:
        if name == "careful":
            blocklist = metadata.get("careful_blocklist")
            hooks.append(CarefulHook(blocklist=blocklist))
        elif name == "freeze":
            allowed = metadata.get("freeze_allowed_tools", [])
            hooks.append(FreezeHook(allowed_tools=allowed))
        else:
            logger.warning(f"未知 skill hook: {name}")
    return hooks


class CarefulHook(StepHook):
    """安全阻断 hook：拦截高温或危险操作."""

    def __init__(self, blocklist: Optional[Dict[str, Dict[str, Any]]] = None):
        self.blocklist = blocklist or self._default_blocklist()

    @staticmethod
    def _default_blocklist() -> Dict[str, Dict[str, Any]]:
        return {
            "heat_pan": {
                "temperature": {
                    "forbidden": ["大火"],
                    "max": 220,
                }
            }
        }

    async def on_before(self, runner, step_rec, tool_name: str, arguments: Dict[str, Any]):
        rules = self.blocklist.get(tool_name, {})
        for param, rule in rules.items():
            value = arguments.get(param)
            if value is None:
                continue

            if isinstance(rule, list):
                if value in rule:
                    raise PermissionError(
                        f"CarefulHook 阻断: {tool_name}.{param}={value} 在禁止列表中"
                    )
                continue

            if isinstance(rule, dict):
                forbidden = rule.get("forbidden", [])
                if value in forbidden:
                    raise PermissionError(
                        f"CarefulHook 阻断: {tool_name}.{param}={value} 在禁止列表中"
                    )
                max_val = rule.get("max")
                if max_val is not None:
                    try:
                        if float(value) > max_val:
                            raise PermissionError(
                                f"CarefulHook 阻断: {tool_name}.{param}={value} 超过最大值 {max_val}"
                            )
                    except (TypeError, ValueError):
                        pass

    async def on_after(self, runner, step_rec, tool_name: str, arguments: Dict[str, Any], result_text: Optional[str]):
        pass

    async def on_error(self, runner, step_rec, tool_name: str, arguments: Dict[str, Any], error: Exception):
        pass


class FreezeHook(StepHook):
    """只读/冻结 hook：只允许调用白名单内的工具."""

    def __init__(self, allowed_tools: Optional[List[str]] = None):
        self.allowed_tools = set(allowed_tools or [])

    async def on_before(self, runner, step_rec, tool_name: str, arguments: Dict[str, Any]):
        if self.allowed_tools and tool_name not in self.allowed_tools:
            raise PermissionError(
                f"FreezeHook 阻断: 工具 {tool_name} 不在允许列表 {sorted(self.allowed_tools)} 中"
            )

    async def on_after(self, runner, step_rec, tool_name: str, arguments: Dict[str, Any], result_text: Optional[str]):
        pass

    async def on_error(self, runner, step_rec, tool_name: str, arguments: Dict[str, Any], error: Exception):
        pass


class SkillHookRegistry:
    """管理 skill 级 hooks 的临时注册与卸载."""

    def __init__(self, runner, hooks: List[StepHook]):
        self.runner = runner
        self.hooks = hooks
        self._original: Optional[List[StepHook]] = None

    def register(self) -> None:
        """将 skill hooks 插到 runner.hooks 列表前."""
        if self._original is not None:
            return
        self._original = list(self.runner.hooks)
        self.runner.hooks = self.hooks + self._original

    def unregister(self) -> None:
        """恢复到原始 hooks 列表."""
        if self._original is None:
            return
        self.runner.hooks = self._original
        self._original = None

    @asynccontextmanager
    async def scope(self):
        """异步上下文管理器：注册 hooks，退出时自动卸载."""
        self.register()
        try:
            yield self
        finally:
            self.unregister()


@asynccontextmanager
async def skill_hooks_scope(runner, hooks: List[StepHook]):
    """将 skill hooks 临时注册到 runner，退出时自动卸载.

    Args:
        runner: StepRunner 实例。
        hooks: 要注册的 StepHook 列表。
    """
    registry = SkillHookRegistry(runner, hooks)
    async with registry.scope():
        yield registry
