"""Agent 消息重建器."""

from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage


def reconstruct_lc_messages(messages: List[Dict[str, Any]]) -> List:
    """从 dict 快照重建 LangChain 消息对象."""
    result = []
    for m in messages:
        t = m.get("type")
        if t == "human":
            result.append(HumanMessage(content=m.get("content", "")))
        elif t == "ai":
            result.append(AIMessage(content=m.get("content", ""), tool_calls=m.get("tool_calls", [])))
        elif t == "tool":
            result.append(ToolMessage(content=m.get("content", ""), tool_call_id=m.get("tool_call_id", "")))
        else:
            # 未知类型，按 HumanMessage 兜底
            result.append(HumanMessage(content=str(m)))
    return result
