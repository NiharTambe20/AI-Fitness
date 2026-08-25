import time
import numpy as np
from utils import calculate_angle, AngleSmoother, BaseExerciseTracker, are_landmarks_valid

class LegRaisesTracker(BaseExerciseTracker):
    """
    Leg Raises Tracker:
    Measures Shoulder -> Hip -> Ankle leg raise angle.
    States: DOWN (>145 deg) <-> RAISED (<110 deg)
    """
    def __init__(self, down_angle=145.0, raised_angle=110.0, debounce_sec=0.4):
        super().__init__("Leg Raises")
        self.down_angle = down_angle
        self.raised_angle = raised_angle
        self.debounce_sec = debounce_sec

        self.state = "DOWN"
        self.last_rep_time = 0.0

        self.left_hip_smoother = AngleSmoother(alpha=0.35)
        self.right_hip_smoother = AngleSmoother(alpha=0.35)

    def process(self, keypoints):
        left_valid = are_landmarks_valid(keypoints, ["left_shoulder", "left_hip", "left_ankle"])
        right_valid = are_landmarks_valid(keypoints, ["right_shoulder", "right_hip", "right_ankle"])

        hip_angles = []
        if left_valid:
            hip_angles.append(self.left_hip_smoother.update(calculate_angle(keypoints["left_shoulder"], keypoints["left_hip"], keypoints["left_ankle"])))
        if right_valid:
            hip_angles.append(self.right_hip_smoother.update(calculate_angle(keypoints["right_shoulder"], keypoints["right_hip"], keypoints["right_ankle"])))

        if not hip_angles:
            if are_landmarks_valid(keypoints, ["left_shoulder", "left_hip", "left_knee"]):
                hip_angles.append(self.left_hip_smoother.update(calculate_angle(keypoints["left_shoulder"], keypoints["left_hip"], keypoints["left_knee"])))
            elif are_landmarks_valid(keypoints, ["right_shoulder", "right_hip", "right_knee"]):
                hip_angles.append(self.right_hip_smoother.update(calculate_angle(keypoints["right_shoulder"], keypoints["right_hip"], keypoints["right_knee"])))

        if not hip_angles:
            return self.build_result("DOWN", feedback=["Position legs in view"], valid=False)

        avg_hip_angle = float(np.mean(hip_angles))
        feedback_list = []
        is_good_form = True
        now = time.time()

        if self.state == "DOWN":
            if avg_hip_angle <= self.raised_angle:
                self.state = "RAISED"
                feedback_list.append("Legs raised! Lower under control")
            else:
                feedback_list.append("Raise Legs")

        elif self.state == "RAISED":
            if avg_hip_angle >= self.down_angle:
                if (now - self.last_rep_time) >= self.debounce_sec:
                    self.rep_count += 1
                    self.last_rep_time = now
                    feedback_list.append("Great Leg Raise!")
                    self.form_scores.append(1)

                self.state = "DOWN"
            else:
                feedback_list.append("Lower Legs")

        if is_good_form and not feedback_list:
            feedback_list.append("GOOD FORM")

        return self.build_result(self.state, primary_angle=avg_hip_angle, feedback=feedback_list, valid=True)
