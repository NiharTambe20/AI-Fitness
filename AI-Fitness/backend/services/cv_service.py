import base64
import cv2
import numpy as np
from typing import Optional, Dict, Any

from pose import PoseDetector
from exercise import ExerciseController, ExerciseRegistry
from assistant import WorkoutSessionData

class CVLiveService:
    """
    Bridge service connecting browser webcam frame streams with Member 3's CV Engine.
    Reuses PoseDetector & ExerciseController without modifying any tracking algorithms.
    """
    def __init__(self, model_path="models/pose_model.pt"):
        self.detector = None
        self.model_path = model_path
        self.active_sessions: Dict[str, ExerciseController] = {}

    def _ensure_detector(self):
        if self.detector is None:
            print("[INFO] Lazy-loading YOLO PoseDetector model for CV Live Service...")
            self.detector = PoseDetector(model_path=self.model_path, conf_threshold=0.25)

    def resolve_exercise_key(self, choice_key: str) -> Optional[str]:
        key = str(choice_key).strip()
        if key in ExerciseRegistry.EXERCISES:
            return key
        for k, (name, _) in ExerciseRegistry.EXERCISES.items():
            if name.lower() == key.lower():
                return k
        return None

    def get_or_create_session(self, session_id: str, exercise_choice: str = "1") -> ExerciseController:
        """
        Gets existing ExerciseController or creates a new one for session_id.
        Validates exercise_choice against ExerciseRegistry.
        """
        self._ensure_detector()
        
        # Validate exercise choice
        resolved_key = self.resolve_exercise_key(exercise_choice)
        if not resolved_key:
            raise ValueError(f"Invalid exercise choice '{exercise_choice}'. Supported exercises: 1-20 or names like 'Squat'.")

        if session_id not in self.active_sessions:
            print(f"[INFO] Initializing new CV live session '{session_id}' for exercise: {exercise_choice} (Key: {resolved_key})")
            self.active_sessions[session_id] = ExerciseController(resolved_key)

        return self.active_sessions[session_id]

    def close_session(self, session_id: str) -> Optional[WorkoutSessionData]:
        """
        Terminates session and returns final WorkoutSessionData summary.
        """
        if session_id in self.active_sessions:
            controller = self.active_sessions.pop(session_id)
            controller.finish_session()
            return controller.create_session_data()
        return None

    def process_frame(
        self,
        controller: ExerciseController,
        frame_bytes: bytes,
        include_annotated_image: bool = True
    ) -> Dict[str, Any]:
        """
        Decodes raw JPEG/PNG bytes, runs YOLO Pose inference & exercise tracker,
        and returns live telemetry payload.
        """
        self._ensure_detector()

        # 1. Decode bytes into OpenCV BGR numpy array
        np_arr = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if frame is None:
            return {
                "status": "error",
                "message": "Could not decode frame image bytes"
            }

        # 2. Process frame with Member 3 PoseDetector & active exercise tracker
        annotated_frame, keypoints, tracker_info = self.detector.process_frame(
            frame,
            tracker=controller.tracker
        )

        if tracker_info is None:
            return {
                "status": "warning",
                "message": "No keypoints detected",
                "exercise": controller.tracker.name,
                "rep_count": controller.tracker.rep_count,
                "form_score": controller.tracker.get_form_score(),
                "state": getattr(controller.tracker, "state", "UNKNOWN"),
                "feedback": ["Position yourself in view"],
                "valid": False,
                "annotated_frame": None
            }

        # 3. Optionally encode annotated frame with skeleton HUD overlay back to base64 JPEG
        annotated_b64 = None
        if include_annotated_image and annotated_frame is not None:
            _, buffer = cv2.imencode('.jpg', annotated_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
            annotated_b64 = "data:image/jpeg;base64," + base64.b64encode(buffer).decode('utf-8')

        # 4. Return live telemetry payload
        return {
            "status": "success",
            "exercise": tracker_info["exercise"],
            "rep_count": tracker_info["rep_count"],
            "state": tracker_info["state"],
            "primary_angle": tracker_info["primary_angle"],
            "secondary_angle": tracker_info.get("secondary_angle"),
            "form_score": tracker_info["form_score"],
            "feedback": tracker_info["feedback"],
            "valid": tracker_info["valid"],
            "annotated_frame": annotated_b64
        }

    def process_base64_frame(
        self,
        controller: ExerciseController,
        base64_str: str,
        include_annotated_image: bool = True
    ) -> Dict[str, Any]:
        """
        Decodes a base64 image data URL string and runs CV processing.
        """
        if "," in base64_str:
            base64_str = base64_str.split(",")[1]

        frame_bytes = base64.b64decode(base64_str)
        return self.process_frame(controller, frame_bytes, include_annotated_image)

cv_live_service = CVLiveService()
