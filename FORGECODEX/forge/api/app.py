import asyncio
from datetime import datetime
from pathlib import Path
import socket
import sys
import time

from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import API_HOST, API_PORT, DB_PATH, MACHINE_ID, TOOL_ID
from forge.db.audit_log import AuditLog
from forge.llm.maintenance_assistant import FORGEMaintenanceAI
from queue import Queue, Empty

class OverrideRequest(BaseModel):
    alert_id: str
    reason_code: int


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, payload: dict) -> None:
        disconnected: list[WebSocket] = []
        for connection in list(self.active_connections):
            try:
                await connection.send_json(payload)
            except Exception:
                disconnected.append(connection)
        for connection in disconnected:
            self.disconnect(connection)


class ForgeAPIState:
    def __init__(self) -> None:
        self.started_at = time.time()
        self.last_prediction = None
        self.current_state = {
            "machine_id": MACHINE_ID,
            "tool_id": TOOL_ID,
            "features": {},
            "prediction": None,
            "decision": None,
            "twin_result": None,
            "alerts": [],
        }
        self.manager = ConnectionManager()
        self.db = AuditLog(DB_PATH)

    def update_state(self, forge_state: dict) -> None:
        self.current_state.update(forge_state)
        self.last_prediction = forge_state.get("prediction", self.last_prediction)

    async def broadcast_state(self, forge_state: dict) -> None:
        self.update_state(forge_state)
        await self.manager.broadcast(
            {
                "machine_id": forge_state.get("machine_id", MACHINE_ID),
                "tool_id": forge_state.get("tool_id", TOOL_ID),
                "feature_vector": forge_state.get("features", {}),
                "prediction": forge_state.get("prediction"),
                "decision": forge_state.get("decision"),
                "twin_result": forge_state.get("twin_result"),
                "stroke_count": forge_state.get("stroke_count"),
                "alert_id": forge_state.get("alert_id"),
            }
        )

    def history(self, hours: int = 24, machine_id: str = MACHINE_ID) -> list[dict]:
        cutoff_query = """
            SELECT predictions.timestamp, predictions.stroke_num, predictions.median_remaining,
                   predictions.failure_probability, predictions.divergence, alerts.alert_level
            FROM predictions
            LEFT JOIN alerts
              ON predictions.machine_id = alerts.machine_id
             AND predictions.stroke_num = alerts.stroke_num
            WHERE predictions.machine_id = ?
            ORDER BY predictions.timestamp DESC
            LIMIT ?
        """
        rows = self.db.conn.execute(cutoff_query, (machine_id, max(1, hours * 120))).fetchall()
        return [
            {
                "timestamp": row["timestamp"],
                "wear_pct": None if row["median_remaining"] is None else max(0.0, 100.0 - float(row["median_remaining"])),
                "prediction": row["median_remaining"],
                "alert": row["alert_level"],
                "stroke_num": row["stroke_num"],
                "failure_probability": row["failure_probability"],
                "divergence": row["divergence"],
            }
            for row in rows
        ]

    def fleet(self) -> list[dict]:
        prediction = self.current_state.get("prediction") or {}
        twin_result = self.current_state.get("twin_result") or {}
        alert_level = twin_result.get("alert_level", "NORMAL")
        return [
            {
                "machine_id": self.current_state.get("machine_id", MACHINE_ID),
                "status": alert_level,
                "last_prediction": prediction.get("median_remaining_strokes"),
                "divergence": twin_result.get("divergence", 0.0),
            }
        ]


app = FastAPI(title="FORGE API")
state_store = ForgeAPIState()
llm_ai = FORGEMaintenanceAI(MACHINE_ID, state_store.db)
state_queue = Queue()

@app.on_event("startup")
async def startup_event():
    async def _broadcaster():
        while True:
            try:
                state = state_queue.get_nowait()
                await state_store.broadcast_state(state)
            except Empty:
                pass
            await asyncio.sleep(0.1)
    asyncio.create_task(_broadcaster())


@app.get("/health")
def get_health() -> dict:
    return {
        "status": "ok",
        "machine_id": MACHINE_ID,
        "uptime": time.time() - state_store.started_at,
        "last_prediction": state_store.last_prediction,
        "host": API_HOST,
        "port": API_PORT,
    }


@app.get("/state")
def get_state() -> dict:
    return state_store.current_state


@app.post("/override")
def post_override(payload: OverrideRequest) -> dict:
    state_store.db.log_override(payload.alert_id, MACHINE_ID, payload.reason_code)
    return {"success": True}


@app.post("/whatsapp-webhook")
async def whatsapp_webhook(request: Request) -> Response:
    try:
        form = await request.form()
        body = str(form.get("Body", "")).strip()
    except Exception:
        body = ""

    alert_id = state_store.current_state.get("alert_id")
    
    if body in ["1", "2", "3", "4"] and alert_id:
        state_store.db.log_override(alert_id, MACHINE_ID, int(body))
        resp_body = f"Override {body} logged successfully."
    else:
        answer = llm_ai.ask(body, state_store.current_state)
        resp_body = str(answer)
        
    xml_str = f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{resp_body}</Message></Response>'
    return Response(content=xml_str, media_type="application/xml")


@app.get("/history")
def get_history(hours: int = 24, machine_id: str = MACHINE_ID) -> list[dict]:
    return state_store.history(hours=hours, machine_id=machine_id)


@app.get("/fleet")
def get_fleet() -> list[dict]:
    return state_store.fleet()


@app.websocket("/live")
async def live_socket(websocket: WebSocket) -> None:
    await state_store.manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        state_store.manager.disconnect(websocket)
    except Exception:
        state_store.manager.disconnect(websocket)


def update_state(forge_state: dict) -> None:
    state_store.update_state(forge_state)


def broadcast_state(forge_state: dict) -> None:
    state_queue.put(forge_state)


def run_app() -> None:
    import uvicorn
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((API_HOST, API_PORT))
    except OSError:
        return
    finally:
        sock.close()
    try:
        uvicorn.run(app, host=API_HOST, port=API_PORT)
    except OSError:
        return
