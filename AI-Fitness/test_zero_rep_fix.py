#!/usr/bin/env python3
"""
Test suite verifying zero-rep workout completion logic, honest AI coaching,
and valid/flawed repetition handling across the FitQuest pipeline.
"""

from fastapi.testclient import TestClient
from backend.main import app
from backend.database import init_db, SessionLocal
from backend.models import WorkoutSessionModel, FormLogModel, AICoachingLogModel
from assistant import AIFitnessAssistant, WorkoutSessionData, UserProfile
from utils.counter import BaseExerciseTracker

def test_zero_rep_and_workout_scenarios():
    print("[TEST] Initializing Zero-Rep & Workout Pipeline Test Suite...")

    init_db()
    db = SessionLocal()
    db.query(AICoachingLogModel).delete()
    db.query(FormLogModel).delete()
    db.query(WorkoutSessionModel).delete()
    db.commit()
    db.close()

    client = TestClient(app)


    # 1. Test BaseExerciseTracker get_form_score on 0 reps
    tracker = BaseExerciseTracker("High Knees")
    assert tracker.rep_count == 0
    assert tracker.get_form_score() == 0.0, f"Expected 0.0 form score for 0 reps, got {tracker.get_form_score()}"
    print("[PASS] BaseExerciseTracker returns 0.0 form score for 0 reps.")

    # 2. Scenario 1: Zero-rep workout session ingestion via POST /api/v1/workouts
    user_res = client.post("/api/v1/users", json={"name": "ZeroRep User", "email": "zerorep@example.com"})
    user_id = user_res.json()["id"]

    zero_rep_payload = {
        "session_data": {
            "user_id": user_id,
            "exercise_id": 1,  # Bicep Curl
            "repetitions": 0,
            "duration_sec": 74,
            "form_score": 0.0
        },
        "form_scores_history": [],
        "feedback_events": ["Position yourself in view"]
    }

    res_zero = client.post("/api/v1/workouts", json=zero_rep_payload)
    assert res_zero.status_code == 201, f"Zero-rep ingestion failed: {res_zero.text}"
    session_zero = res_zero.json()
    assert session_zero["repetitions"] == 0, "Rep count should be 0"
    assert session_zero["form_score"] == 0.0, "Form score should be 0.0"

    ai_logs = session_zero.get("ai_coaching_logs", [])
    assert len(ai_logs) > 0, "AI coaching log missing for zero-rep session"
    ai_feedback = ai_logs[0]["response"].lower()

    # Honest AI check: MUST NOT praise form / MUST report 0 valid reps


    forbidden_phrases = ["outstanding biomechanics", "excellent form", "maintained proper joint alignment"]
    for phrase in forbidden_phrases:
        assert phrase not in ai_feedback, f"AI feedback incorrectly contained praised phrase '{phrase}' on 0 reps!"

    assert "no valid repetitions" in ai_feedback or "0 reps" in ai_feedback or "camera" in ai_feedback or "n/a" in ai_feedback, (
        f"AI feedback lacked zero-rep notification: '{ai_feedback}'"
    )
    print(f"[PASS] Scenario 1 (Zero Reps): Verified 0 reps, 0.0 form score, and honest AI feedback.")

    # 3. Scenario 2: Valid repetitions workout session (e.g. 10 reps, 95% form)
    valid_rep_payload = {
        "session_data": {
            "user_id": user_id,
            "exercise_id": 2,  # Squat
            "repetitions": 10,
            "duration_sec": 60,
            "form_score": 95.0
        },
        "form_scores_history": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        "feedback_events": ["Good squat depth"]
    }

    res_valid = client.post("/api/v1/workouts", json=valid_rep_payload)
    assert res_valid.status_code == 201, f"Valid rep ingestion failed: {res_valid.text}"
    session_valid = res_valid.json()
    assert session_valid["repetitions"] == 10, "Rep count mismatch"
    assert session_valid["form_score"] == 95.0, "Form score mismatch"
    ai_valid_logs = session_valid.get("ai_coaching_logs", [])
    assert len(ai_valid_logs) > 0
    print(f"[PASS] Scenario 2 (Valid Reps): Verified 10 reps, 95.0% form score, and coaching feedback.")

    # 4. Scenario 3: Poor form workout session (e.g. 10 reps, 60% form)
    poor_form_payload = {
        "session_data": {
            "user_id": user_id,
            "exercise_id": 2,  # Squat
            "repetitions": 10,
            "duration_sec": 65,
            "form_score": 60.0
        },
        "form_scores_history": [1, 0, 1, 0, 0, 1, 0, 1, 0, 0],
        "feedback_events": ["Incomplete depth logged"]
    }

    res_poor = client.post("/api/v1/workouts", json=poor_form_payload)
    assert res_poor.status_code == 201
    session_poor = res_poor.json()
    assert session_poor["form_score"] == 60.0
    ai_poor_logs = session_poor.get("ai_coaching_logs", [])
    assert len(ai_poor_logs) > 0
    poor_ai_text = ai_poor_logs[0]["response"].lower()
    assert "form" in poor_ai_text or "attention" in poor_ai_text or "cues" in poor_ai_text
    print(f"[PASS] Scenario 3 (Poor Form): Verified 60.0% form score and corrective feedback.")

    # 5. Scenario 4: Verify workout history retrieves sessions correctly
    res_hist = client.get(f"/api/v1/workouts/user/{user_id}")
    assert res_hist.status_code == 200
    history = res_hist.json()
    assert len(history) == 3, f"Expected 3 workout sessions in history, got {len(history)}"
    print(f"[PASS] Scenario 4 (Workout History): History retrieved {len(history)} sessions correctly.")

    # 6. Scenario 5: Verify AI Coach Chatbot works independently
    res_qa = client.post("/api/v1/ai/qa", json={"question": "What is the best way to improve squat depth?"})
    assert res_qa.status_code == 200
    assert res_qa.json().get("status") == "success"
    assert len(res_qa.json().get("answer", "")) > 50
    print("[PASS] Scenario 5 (AI Chatbot): Verified independent Q&A operating normally.")

    print("\n[SUCCESS] All Zero-Rep Fix & Workout Pipeline scenarios passed cleanly!")

if __name__ == "__main__":
    test_zero_rep_and_workout_scenarios()
