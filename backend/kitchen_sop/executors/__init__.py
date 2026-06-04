"""执行器模块：提供多种 Skill 执行模式."""


# 延迟导入，避免在仅使用 Demo 模式时加载 LangChain 相关依赖
def __getattr__(name):
    if name == "run_demo_mode":
        from .demo import run_demo_mode
        return run_demo_mode
    if name == "run_agent_mode":
        from .agent import run_agent_mode
        return run_agent_mode
    if name == "resume_run":
        from .resume import resume_run
        return resume_run
    if name == "rollback_run":
        from .rollback import rollback_run
        return rollback_run
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
