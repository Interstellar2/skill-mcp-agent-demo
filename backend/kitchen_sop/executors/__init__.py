"""执行器模块：提供 Demo 和 Agent 两种执行模式."""


# 延迟导入，避免在仅使用 Demo 模式时加载 LangChain 相关依赖
def __getattr__(name):
    if name == "run_demo_mode":
        from .demo import run_demo_mode

        return run_demo_mode
    if name == "run_agent_mode":
        from .agent import run_agent_mode

        return run_agent_mode
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
