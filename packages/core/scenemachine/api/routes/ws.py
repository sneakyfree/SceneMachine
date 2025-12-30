"""WebSocket route handlers for real-time updates."""

import json
import logging
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from scenemachine.api.websocket import manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Main WebSocket endpoint for real-time updates.

    Clients can send JSON messages to:
    - Subscribe to project updates: {"action": "subscribe", "project_id": "..."}
    - Subscribe to job updates: {"action": "subscribe_job", "job_id": "..."}
    - Unsubscribe: {"action": "unsubscribe", "project_id": "..."}
    - Ping: {"action": "ping"}
    """
    connection_id = str(uuid4())

    try:
        await manager.connect(websocket, connection_id)

        while True:
            # Wait for messages from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                action = message.get("action")

                if action == "subscribe":
                    project_id = message.get("project_id")
                    if project_id:
                        await manager.subscribe_to_project(connection_id, project_id)
                        await websocket.send_json({
                            "type": "subscribed",
                            "project_id": project_id,
                        })

                elif action == "subscribe_job":
                    job_id = message.get("job_id")
                    if job_id:
                        await manager.subscribe_to_job(connection_id, job_id)
                        await websocket.send_json({
                            "type": "subscribed_job",
                            "job_id": job_id,
                        })

                elif action == "unsubscribe":
                    project_id = message.get("project_id")
                    if project_id:
                        await manager.unsubscribe_from_project(connection_id, project_id)
                        await websocket.send_json({
                            "type": "unsubscribed",
                            "project_id": project_id,
                        })

                elif action == "unsubscribe_job":
                    job_id = message.get("job_id")
                    if job_id:
                        await manager.unsubscribe_from_job(connection_id, job_id)
                        await websocket.send_json({
                            "type": "unsubscribed_job",
                            "job_id": job_id,
                        })

                elif action == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "connection_id": connection_id,
                        "connections": manager.get_connection_count(),
                    })

                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown action: {action}",
                    })

            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON",
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error for {connection_id}: {e}")
    finally:
        await manager.disconnect(connection_id)


@router.get("/ws/stats")
async def websocket_stats() -> dict:
    """Get WebSocket connection statistics."""
    return {
        "active_connections": manager.get_connection_count(),
        "project_subscriptions": len(manager.project_subscriptions),
        "job_subscriptions": len(manager.job_subscriptions),
    }
