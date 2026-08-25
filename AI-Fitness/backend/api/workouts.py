import json
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.workout import WorkoutSessionCreate, WorkoutSessionResponse
from backend.services.workout_service import workout_service
from backend.services.cv_service import cv_live_service

router = APIRouter(prefix="/workouts", tags=["Workouts"])

class WorkoutSessionIngestRequest(BaseModel):
    session_data: WorkoutSessionCreate
    form_scores_history: Optional[List[int]] = None
    feedback_events: Optional[List[str]] = None

class LiveFrameProcessRequest(BaseModel):
    session_id: str = "default_session"
    exercise_choice: str = "1"
    frame_data: str
    include_annotated_image: Optional[bool] = True

class LiveSessionStopRequest(BaseModel):
    session_id: str = "default_session"

@router.post("", response_model=WorkoutSessionResponse, status_code=status.HTTP_201_CREATED, summary="Ingest Workout Session & Generate AI Coaching")
@router.post("/", response_model=WorkoutSessionResponse, status_code=status.HTTP_201_CREATED, summary="Ingest Workout Session & Generate AI Coaching")
def ingest_workout_session(payload: WorkoutSessionIngestRequest, db: Session = Depends(get_db)):
    """
    Receives completed CV workout telemetry payload, persists workout session & form logs,
    triggers Member 4 AI Fitness Assistant, stores AI coaching log, and returns full details.
    """
    try:
        session = workout_service.create_workout_session(
            db=db,
            session_in=payload.session_data,
            form_scores_history=payload.form_scores_history,
            feedback_events=payload.feedback_events
        )
        return session
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Failed to ingest workout session: {err}")

@router.post("/live/process-frame", summary="Process Live Camera Frame with CV Engine")
def process_live_frame(payload: LiveFrameProcessRequest):
    """
    HTTP endpoint processing a single base64 camera frame through Member 3 YOLO Pose Engine.
    Validates exercise_choice and returns real-time telemetry + optional skeleton overlay frame.
    """
    try:
        controller = cv_live_service.get_or_create_session(
            session_id=payload.session_id,
            exercise_choice=payload.exercise_choice
        )
        telemetry = cv_live_service.process_base64_frame(
            controller=controller,
            base64_str=payload.frame_data,
            include_annotated_image=payload.include_annotated_image
        )
        return telemetry
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Live frame processing error: {err}")

@router.post("/live/stop-session", summary="Stop Live CV Workout Session")
def stop_live_session(payload: LiveSessionStopRequest):
    """
    Stops a live CV session and returns final summary telemetry.
    """
    summary = cv_live_service.close_session(payload.session_id)
    if not summary:
        return {"status": "info", "message": "No active session found"}
    return {
        "status": "success",
        "exercise": summary.exercise_name,
        "total_reps": summary.rep_count,
        "duration_sec": summary.duration_sec,
        "form_score": summary.form_score
    }

@router.websocket("/live-ws/{exercise_choice}")
async def live_workout_websocket(websocket: WebSocket, exercise_choice: str):
    """
    WebSocket endpoint for real-time live webcam frame streaming and telemetry.
    """
    await websocket.accept()
    session_id = f"ws_session_{id(websocket)}"

    try:
        controller = cv_live_service.get_or_create_session(
            session_id=session_id,
            exercise_choice=exercise_choice
        )
    except ValueError as err:
        await websocket.send_json({"status": "error", "message": str(err)})
        await websocket.close(code=1008)
        return

    try:
        while True:
            data = await websocket.receive_text()
            if not data:
                continue

            # Handle incoming frame payload
            frame_data = data
            if data.startswith("{"):
                try:
                    parsed = json.loads(data)
                    frame_data = parsed.get("frame_data", "")
                except json.JSONDecodeError:
                    pass

            if not frame_data:
                continue

            telemetry = cv_live_service.process_base64_frame(
                controller=controller,
                base64_str=frame_data,
                include_annotated_image=True
            )
            await websocket.send_json(telemetry)

    except WebSocketDisconnect:
        print(f"[INFO] WebSocket disconnected for session {session_id}")
    finally:
        cv_live_service.close_session(session_id)

@router.get("/{session_id}", response_model=WorkoutSessionResponse, summary="Get Workout Session details by ID")
def get_workout_session(session_id: int, db: Session = Depends(get_db)):
    """
    Retrieves full workout session details including form logs and AI coaching history.
    """
    session = workout_service.get_workout_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Workout session with ID {session_id} not found.")
    return session

@router.get("/user/{user_id}", response_model=List[WorkoutSessionResponse], summary="Get Workout History for a User")
def get_user_workouts(user_id: int, db: Session = Depends(get_db)):
    """
    Retrieves historical workout sessions for a given user.
    """
    return workout_service.get_user_workouts(db, user_id)
