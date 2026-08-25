#!/usr/bin/env python3
"""
Test suite for Phase 4 REST API endpoints & AI orchestration service.
"""

from fastapi.testclient import TestClient
from backend.main import app
from backend.database import init_db

def test_api_endpoints():
    print("[TEST] Initializing REST API & Service Layer test suite...")

    # Initialize DB & Seed exercises
    init_db()

    client = TestClient(app)

    # 1. Test Root & Health Endpoints
    res_root = client.get("/")
    assert res_root.status_code == 200, "Root endpoint failed"

    res_health = client.get("/health")
    assert res_health.status_code == 200, "Health check failed"
    print("[PASS] Root and Health endpoints verified.")

    # 2. Test Exercise Catalogue Endpoint (Verify 20 seeded items)
    res_exercises = client.get("/api/v1/exercises")
    assert res_exercises.status_code == 200, "Exercise list endpoint failed"
    exercises = res_exercises.json()
    assert len(exercises) == 20, f"Expected 20 seeded exercises, found {len(exercises)}"
    print(f"[PASS] GET /api/v1/exercises verified ({len(exercises)} exercises returned).")

    # 3. Test User Creation Endpoint
    user_payload = {
        "name": "Alex Strength",
        "email": "alex.strength@example.com",
        "fitness_goal": "Hypertrophy",
        "experience_level": "Intermediate"
    }
    res_user = client.post("/api/v1/users", json=user_payload)
    assert res_user.status_code == 201, f"User creation failed: {res_user.text}"
    user_data = res_user.json()
    user_id = user_data["id"]
    assert user_data["name"] == "Alex Strength", "User name mismatch"
    print(f"[PASS] POST /api/v1/users created user ID {user_id}.")

    # 4. Test Get User Endpoint
    res_get_user = client.get(f"/api/v1/users/{user_id}")
    assert res_get_user.status_code == 200, "Get user failed"
    assert res_get_user.json()["email"] == "alex.strength@example.com"
    print("[PASS] GET /api/v1/users/{user_id} verified.")

    # 5. Test Workout Ingestion & AI Coaching Orchestration Endpoint
    workout_payload = {
        "session_data": {
            "user_id": user_id,
            "exercise_id": exercises[0]["id"],  # Bicep Curl
            "repetitions": 12,
            "duration_sec": 60,
            "form_score": 91.7
        },
        "form_scores_history": [1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1],
        "feedback_events": ["Curl higher on rep 6"]
    }
    res_workout = client.post("/api/v1/workouts", json=workout_payload)
    assert res_workout.status_code == 201, f"Workout ingestion failed: {res_workout.text}"
    session_data = res_workout.json()
    session_id = session_data["id"]
    assert session_data["repetitions"] == 12, "Repetition count mismatch"
    assert session_data["form_score"] == 91.7, "Form score mismatch"
    assert len(session_data["form_logs"]) == 1, "Form log event missing"
    print(f"[PASS] POST /api/v1/workouts ingested session ID {session_id} with form logs.")

    # 6. Test GET Workout Session Details Endpoint
    res_session = client.get(f"/api/v1/workouts/{session_id}")
    assert res_session.status_code == 200, "Get workout session failed"
    assert res_session.json()["id"] == session_id
    print("[PASS] GET /api/v1/workouts/{session_id} verified.")

    # 7. Test GET User Workout History Endpoint
    res_history = client.get(f"/api/v1/workouts/user/{user_id}")
    assert res_history.status_code == 200, "Get user workout history failed"
    assert len(res_history.json()) >= 1, "Workout history should contain at least 1 session"
    print("[PASS] GET /api/v1/workouts/user/{user_id} verified.")

    # 8. Test Standalone AI Coaching Endpoint
    ai_coaching_payload = {
        "session_data": {
            "exercise_name": "Squat",
            "rep_count": 15,
            "duration_sec": 90,
            "form_score": 80.0,
            "form_scores_history": [1, 1, 1, 0, 1],
            "feedback_events": ["Squat deeper next time"]
        },
        "user_profile": {
            "fitness_goal": "Strength",
            "experience_level": "Intermediate"
        }
    }
    res_ai_coaching = client.post("/api/v1/ai/coaching", json=ai_coaching_payload)
    assert res_ai_coaching.status_code == 200, f"AI coaching failed: {res_ai_coaching.text}"
    ai_data = res_ai_coaching.json()
    assert ai_data["status"] == "success"
    assert "coaching_feedback" in ai_data
    print("[PASS] POST /api/v1/ai/coaching verified.")

    # 9. Test Standalone Fitness Q&A Endpoint
    qa_payload = {
        "question": "What is the best form cue for bicep curls?",
        "user_profile": {
            "fitness_goal": "Hypertrophy",
            "experience_level": "Intermediate"
        }
    }
    res_qa = client.post("/api/v1/ai/qa", json=qa_payload)
    assert res_qa.status_code == 200, "Fitness Q&A failed"
    qa_data = res_qa.json()
    assert qa_data["status"] == "success"
    assert "answer" in qa_data
    print("[PASS] POST /api/v1/ai/qa verified.")

    print("\n[SUCCESS] All REST API & AI Service Layer tests passed cleanly!")

if __name__ == "__main__":
    test_api_endpoints()
