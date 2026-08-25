import time
import numpy as np
from utils import calculate_angle, AngleSmoother, BaseExerciseTracker, are_landmarks_valid

class SitUpsTracker(BaseExerciseTracker):
    """
    Sit-Ups Tracker:
    Measures Shoulder -> Hip -> Knee angle.
    States: DOWN (>130 deg) <-> UP (<90 deg)
    """
    def __init__(self, down_angle=130.0, up_angle=90.0, debounce_sec=0.4):
        super().__init__("Sit-ups")
        self.down_angle = down_angle
        self.up_angle = up_angle
        self.debounce_sec = debounce_sec

        self.state = "DOWN"
        self.last_rep_time = 0.0

        self.left_hip_smoother = AngleSmoother(alpha=0.35)
        self.right_hip_smoother = AngleSmoother(alpha=0.35)
        self.min_hip_angle_in_rep = 180.0

    def process(self, keypoints):
        left_valid = are_landmarks_valid(keypoints, ["left_shoulder", "left_hip", "left_knee"])
        right_valid = are_landmarks_valid(keypoints, ["right_shoulder", "right_hip", "right_knee"])

        hip_angles = []
        if left_valid:
            hip_angles.append(self.left_hip_smoother.update(calculate_angle(keypoints["left_shoulder"], keypoints["left_hip"], keypoints["left_knee"])))
        if right_valid:
            hip_angles.append(self.right_hip_smoother.update(calculate_angle(keypoints["right_shoulder"], keypoints["right_hip"], keypoints["right_knee"])))

        if not hip_angles:
            if are_landmarks_valid(keypoints, ["left_shoulder", "left_hip", "left_ankle"]):
                hip_angles.append(self.left_hip_smoother.update(calculate_angle(keypoints["left_shoulder"], keypoints["left_hip"], keypoints["left_ankle"])))
            elif are_landmarks_valid(keypoints, ["right_shoulder", "right_hip", "right_ankle"]):
                hip_angles.append(self.right_hip_smoother.update(calculate_angle(keypoints["right_shoulder"], keypoints["right_hip"], keypoints["right_ankle"])))

        if not hip_angles:
            return self.build_result("DOWN", feedback=["Position torso in view"], valid=False)

        avg_hip_angle = float(np.mean(hip_angles))
        feedback_list = []
        is_good_form = True
        now = time.time()

        if self.state == "DOWN":
            if avg_hip_angle <= self.up_angle:
                self.state = "UP"
                self.min_hip_angle_in_rep = avg_hip_angle
                feedback_list.append("Good height! Go back down")
            else:
                feedback_list.append("Sit Up")

        elif self.state == "UP":
            if avg_hip_angle < self.min_hip_angle_in_rep:
                self.min_hip_angle_in_rep = avg_hip_angle

            if avg_hip_angle >= self.down_angle:
                if (now - self.last_rep_time) >= self.debounce_sec:
                    self.rep_count += 1
                    self.last_rep_time = now

                    if self.min_hip_angle_in_rep <= self.up_angle:
                        feedback_list.append("Great Rep!")
                    else:
                        feedback_list.append("Sit up higher next time")
                        is_good_form = False

                    self.form_scores.append(1 if is_good_form else 0)

                self.state = "DOWN"
                self.min_hip_angle_in_rep = 180.0
            else:
                feedback_list.append("Go back down")

        if is_good_form and not feedback_list:
            feedback_list.append("GOOD FORM")

        return self.build_result(self.state, primary_angle=avg_hip_angle, feedback=feedback_list, valid=True)
