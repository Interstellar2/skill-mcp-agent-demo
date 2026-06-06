"""WebSocket 连接管理、广播与 HITL 消息处理."""

from typing import Dict, List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

_connections: Dict[str, List[WebSocket]] = {}


async def connect(run_id: str, websocket: WebSocket):
    await websocket.accept()
    if run_id not in _connections:
        _connections[run_id] = []
    _connections[run_id].append(websocket)


def disconnect(run_id: str, websocket: WebSocket):
    if run_id in _connections:
        if websocket in _connections[run_id]:
            _connections[run_id].remove(websocket)
        if not _connections[run_id]:
            del _connections[run_id]


async def broadcast_to_run(run_id: str, message: dict):
    if run_id not in _connections:
        return
    dead = []
    for ws in _connections[run_id]:
        try:
            await ws.send_json(message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        if ws in _connections[run_id]:
            _connections[run_id].remove(ws)
    if run_id in _connections and not _connections[run_id]:
        del _connections[run_id]


@router.websocket("/ws/run/{run_id}")
async def ws_run(websocket: WebSocket, run_id: str):
    await connect(run_id, websocket)
    try:
        from ..tracker import RunTracker

        run = RunTracker.load_run(run_id)
        if run:
            await websocket.send_json({"type": "init", "run": run.to_dict()})
        else:
            await websocket.send_json({"type": "init", "run": None})

        while True:
            msg = await websocket.receive_json()
            msg_type = msg.get("type")
            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            elif msg_type == "hitl_approval":
                from .execution_manager import _active_runs

                active = _active_runs.get(run_id)
                if active and active.hitl_bridge:
                    active.hitl_bridge.submit_approval(
                        msg.get("decision"),
                        msg.get("modified_arguments"),
                    )
                    await websocket.send_json({"type": "hitl_approval_ack"})
                else:
                    await websocket.send_json(
                        {"type": "error", "message": "No pending HITL for this run"}
                    )
    except WebSocketDisconnect:
        pass
    finally:
        disconnect(run_id, websocket)
