import time
import numpy as np
from utils import calculate_angle, AngleSmoother, BaseExerciseTracker, are_landmarks_valid

class PlankTracker(BaseExerciseTracker):
    """
    Plank Tracker:
    Measures Shoulder -> Hip -> Ankle straightness (>150 deg).
    Increments hold time (seconds) as rep_count.
    """
    def __init__(self, min_straight_angle=150.0):
        super().__init__("Plank")
        self.min_straight_angle = min_straight_angle
        self.state = "HOLDING"
        self.start_hold_time = None
        self.total_hold_sec = 0
        self.last_increment_time = time.time()
        self.body_line_smoother = AngleSmoother(alpha=0.35)

    def process(self, keypoints):
        left_valid = are_landmarks_valid(keypoints, ["left_shoulder", "left_hip", "left_ankle"])
        right_valid = are_landmarks_valid(keypoints, ["right_shoulder", "right_hip", "right_ankle"])

        body_angles = []
        if left_valid:
            body_angles.append(self.body_line_smoother.update(calculate_angle(keypoints["left_shoulder"], keypoints["left_hip"], keypoints["left_ankle"])))
        if right_valid:
            body_angles.append(self.body_line_smoother.update(calculate_angle(keypoints["right_shoulder"], keypoints["right_hip"], keypoints["right_ankle"])))

        if not body_angles:
            if are_landmarks_valid(keypoints, ["left_shoulder", "left_hip", "left_knee"]):
                body_angles.append(self.body_line_smoother.update(calculate_angle(keypoints["left_shoulder"], keypoints["left_hip"], keypoints["left_knee"])))
            elif are_landmarks_valid(keypoints, ["right_shoulder", "right_hip", "right_knee"]):
                body_angles.append(self.body_line_smoother.update(calculate_angle(keypoints["right_shoulder"], keypoints["right_hip"], keypoints["right_knee"])))

        if not body_angles:
            return self.build_result("HOLDING", feedback=["Position body in view"], valid=False)

        avg_body_angle = float(np.mean(body_angles))
        feedback_list = []
        is_good_form = True
        now = time.time()

        if avg_body_angle < self.min_straight_angle:
            feedback_list.append("Keep hips aligned / straight")
            is_good_form = False
        else:
            if now - self.last_increment_time >= 1.0:
                self.total_hold_sec += 1
                self.rep_count = self.total_hold_sec
                self.last_increment_time = now
            feedback_list.append(f"Hold Plank! {self.total_hold_sec}s")
            self.form_scores.append(1)

        return self.build_result("HOLDING", primary_angle=avg_body_angle, feedback=feedback_list, valid=True)
