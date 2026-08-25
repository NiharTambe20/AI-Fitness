import time
import numpy as np
from utils import calculate_angle, AngleSmoother, BaseExerciseTracker, are_landmarks_valid

class GluteBridgeTracker(BaseExerciseTracker):
    """
    Glute Bridge Tracker:
    Measures Shoulder -> Hip -> Knee angle.
    States: DOWN (<130 deg) <-> BRIDGE (>160 deg)
    """
    def __init__(self, down_angle=130.0, bridge_angle=160.0, debounce_sec=0.4):
        super().__init__("Glute Bridge")
        self.down_angle = down_angle
        self.bridge_angle = bridge_angle
        self.debounce_sec = debounce_sec

        self.state = "DOWN"
        self.last_rep_time = 0.0

        self.left_hip_smoother = AngleSmoother(alpha=0.35)
        self.right_hip_smoother = AngleSmoother(alpha=0.35)
        self.max_angle_in_rep = 0.0

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

        avg_hip_angle = float(np.mean(hip_angles))
        feedback_list = []
        is_good_form = True
        now = time.time()

        if self.state == "DOWN":
            if avg_hip_angle >= self.bridge_angle:
                self.state = "BRIDGE"
                self.max_angle_in_rep = avg_hip_angle
                feedback_list.append("Squeeze glutes! Lower hips")
            else:
                feedback_list.append("Lift Hips")

        elif self.state == "BRIDGE":
            if avg_hip_angle > self.max_angle_in_rep:
                self.max_angle_in_rep = avg_hip_angle

            if avg_hip_angle <= self.down_angle:
                if (now - self.last_rep_time) >= self.debounce_sec:
                    self.rep_count += 1
                    self.last_rep_time = now

                    if self.max_angle_in_rep >= self.bridge_angle:
                        feedback_list.append("Great Bridge!")
                    else:
                        feedback_list.append("Lift hips higher next time")
                        is_good_form = False

                    self.form_scores.append(1 if is_good_form else 0)

                self.state = "DOWN"
                self.max_angle_in_rep = 0.0
            else:
                feedback_list.append("Lower Hips")

        if is_good_form and not feedback_list:
            feedback_list.append("GOOD FORM")

        return self.build_result(self.state, primary_angle=avg_hip_angle, feedback=feedback_list, valid=True)
