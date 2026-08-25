import time
import numpy as np
from utils import calculate_angle, AngleSmoother, BaseExerciseTracker, are_landmarks_valid

class HighKneesTracker(BaseExerciseTracker):
    """
    High Knees Tracker:
    Measures Shoulder -> Hip -> Knee angle.
    States: DOWN (>130 deg) <-> HIGH_KNEE (<95 deg)
    """
    def __init__(self, down_angle=130.0, high_knee_angle=95.0, debounce_sec=0.3):
        super().__init__("High Knees")
        self.down_angle = down_angle
        self.high_knee_angle = high_knee_angle
        self.debounce_sec = debounce_sec

        self.state = "DOWN"
        self.last_rep_time = 0.0

        self.left_hip_smoother = AngleSmoother(alpha=0.35)
        self.right_hip_smoother = AngleSmoother(alpha=0.35)

    def process(self, keypoints):
        left_valid = are_landmarks_valid(keypoints, ["left_shoulder", "left_hip", "left_knee"])
        right_valid = are_landmarks_valid(keypoints, ["right_shoulder", "right_hip", "right_knee"])

        hip_angles = []
        if left_valid:
            hip_angles.append(self.left_hip_smoother.update(calculate_angle(keypoints["left_shoulder"], keypoints["left_hip"], keypoints["left_knee"])))
        if right_valid:
            hip_angles.append(self.right_hip_smoother.update(calculate_angle(keypoints["right_shoulder"], keypoints["right_hip"], keypoints["right_knee"])))

        if not hip_angles:
            return self.build_result("DOWN", feedback=["Position torso and legs in view"], valid=False)

        min_hip_angle = float(np.min(hip_angles))
        feedback_list = []
        is_good_form = True
        now = time.time()

        if self.state == "DOWN":
            if min_hip_angle <= self.high_knee_angle:
                self.state = "HIGH_KNEE"
                feedback_list.append("High knee reached!")
            else:
                feedback_list.append("Drive Knee High")

        elif self.state == "HIGH_KNEE":
            if min_hip_angle >= self.down_angle:
                if (now - self.last_rep_time) >= self.debounce_sec:
                    self.rep_count += 1
                    self.last_rep_time = now
                    feedback_list.append("Great Knee Drive!")
                    self.form_scores.append(1)

                self.state = "DOWN"
            else:
                feedback_list.append("Lower Knee")

        if is_good_form and not feedback_list:
            feedback_list.append("GOOD FORM")

        return self.build_result(self.state, primary_angle=min_hip_angle, feedback=feedback_list, valid=True)
