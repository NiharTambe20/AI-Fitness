# pyrefly: ignore [missing-import]
import cv2
import os
import time
import numpy as np
from ultralytics import YOLO

class PoseDetector:
    """
    YOLO Pose detector with real-time HUD rendering, joint tracking,
    and modular exercise repetition counting.
    """
    KEYPOINT_MAP = {
        "nose": 0,
        "left_eye": 1, "right_eye": 2,
        "left_ear": 3, "right_ear": 4,
        "left_shoulder": 5, "right_shoulder": 6,
        "left_elbow": 7, "right_elbow": 8,
        "left_wrist": 9, "right_wrist": 10,
        "left_hip": 11, "right_hip": 12,
        "left_knee": 13, "right_knee": 14,
        "left_ankle": 15, "right_ankle": 16,
    }

    def __init__(self, model_path="models/pose_model.pt", conf_threshold=0.25):
        self.conf_threshold = conf_threshold
        self.model_path = model_path
        
        if not os.path.exists("models"):
            os.makedirs("models")
            
        print(f"[INFO] Initializing YOLO Pose model...")
        if not os.path.exists(model_path):
            print(f"[INFO] Pretrained weights not found at {model_path}. Loading yolov8n-pose.pt...")
            self.model = YOLO("yolov8n-pose.pt")
            self.model.save(model_path)
            print(f"[INFO] Saved pretrained weights to {model_path}")
        else:
            self.model = YOLO(model_path)
            
        print("[INFO] YOLO Pose model loaded successfully.")

    def process_frame(self, frame, tracker=None):
        results = self.model(frame, verbose=False)
        annotated_frame = results[0].plot()

        keypoints = {}
        body_detected = False

        if len(results) > 0 and results[0].keypoints is not None and len(results[0].keypoints.data) > 0:
            person_kpts = results[0].keypoints.data[0].cpu().numpy()

            for kp_name, kp_idx in self.KEYPOINT_MAP.items():
                if kp_idx < len(person_kpts):
                    x, y, conf = person_kpts[kp_idx]
                    keypoints[kp_name] = {
                        "x": float(x),
                        "y": float(y),
                        "conf": float(conf),
                        "valid": bool(conf >= self.conf_threshold)
                    }

            # Body is detected if any key upper body / torso landmarks are visible
            core_landmarks = ["left_shoulder", "right_shoulder", "left_elbow", "right_elbow", "left_hip", "right_hip"]
            valid_core_count = sum(1 for lm in core_landmarks if keypoints.get(lm, {}).get("valid", False))
            body_detected = (valid_core_count >= 1)

        tracker_info = None
        if tracker is not None:
            tracker_info = tracker.process(keypoints)
            self.draw_hud(annotated_frame, tracker_info, body_detected)

        return annotated_frame, keypoints, tracker_info

    def draw_hud(self, frame, tracker_info, body_detected):
        if tracker_info is None:
            return

        h, w, _ = frame.shape

        overlay = frame.copy()
        cv2.rectangle(overlay, (10, 10), (370, 185), (20, 20, 20), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

        cv2.putText(frame, f"EXERCISE: {tracker_info['exercise'].upper()}", (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2, cv2.LINE_AA)
        
        rep_text = f"REPS: {tracker_info['rep_count']}"
        cv2.putText(frame, rep_text, (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2, cv2.LINE_AA)

        state_text = f"STATE: {tracker_info['state']}"
        state_color = (0, 255, 255) if tracker_info['state'] in ["UP", "STANDING"] else (255, 165, 0)
        cv2.putText(frame, state_text, (180, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, state_color, 2, cv2.LINE_AA)

        angle_str = f"{tracker_info['primary_angle']} deg" if tracker_info.get('primary_angle') is not None else "N/A"
        cv2.putText(frame, f"Joint Angle: {angle_str}", (20, 105), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)

        if not tracker_info.get("valid", False):
            cv2.putText(frame, "STATUS: Body Not Fully Detected", (20, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2, cv2.LINE_AA)
        else:
            feedback_str = " | ".join(tracker_info["feedback"])
            form_color = (0, 255, 0) if "GOOD FORM" in feedback_str or "Good" in feedback_str or "Great" in feedback_str else (0, 165, 255)
            cv2.putText(frame, f"FORM: {feedback_str}", (20, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.5, form_color, 2, cv2.LINE_AA)

    def start_stream(self, camera_index=0, window_name="AI Fitness Engine"):
        cap = cv2.VideoCapture(camera_index)

        if not cap.isOpened():
            print(f"[ERROR] Could not open video device at index {camera_index}")
            return

        print("[INFO] Camera stream started.")
        print("[INFO] Press 'q' to quit.")

        prev_time = time.time()

        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    print("[WARNING] Failed to grab frame. Exiting.")
                    break

                annotated_frame, keypoints, tracker_info = self.process_frame(frame)

                curr_time = time.time()
                fps = 1.0 / (curr_time - prev_time + 1e-6)
                prev_time = curr_time
                cv2.putText(annotated_frame, f"FPS: {int(fps)}", (frame.shape[1] - 110, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)

                cv2.imshow(window_name, annotated_frame)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("[INFO] User pressed 'q'. Stopping stream.")
                    break
        finally:
            cap.release()
            cv2.destroyAllWindows()
            print("[INFO] Camera stream stopped cleanly.")

if __name__ == "__main__":
    detector = PoseDetector(model_path="models/pose_model.pt", conf_threshold=0.25)
    detector.start_stream()
