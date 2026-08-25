import time
import numpy as np
from utils import calculate_angle, AngleSmoother, BaseExerciseTracker, are_landmarks_valid

class SquatTracker(BaseExerciseTracker):
    """
    Squat Repetition Tracker & Form Evaluator.
    States: STANDING (>150 deg) <-> SQUAT (<110 deg)
    """
    def __init__(self, standing_angle=150.0, squat_angle=110.0, debounce_sec=0.4):
        super().__init__("Squat")
        self.standing_angle = standing_angle
        self.squat_angle = squat_angle
        self.debounce_sec = debounce_sec

        self.state = "STANDING"
        self.last_rep_time = 0.0

        self.left_knee_smoother = AngleSmoother(alpha=0.35)
        self.right_knee_smoother = AngleSmoother(alpha=0.35)
        self.torso_smoother = AngleSmoother(alpha=0.35)

        self.min_knee_angle_in_rep = 180.0

    def process(self, keypoints):
        left_valid = are_landmarks_valid(keypoints, ["left_hip", "left_knee", "left_ankle"])
        right_valid = are_landmarks_valid(keypoints, ["right_hip", "right_knee", "right_ankle"])

        knee_angles = []
        if left_valid:
            raw_l = calculate_angle(keypoints["left_hip"], keypoints["left_knee"], keypoints["left_ankle"])
            knee_angles.append(self.left_knee_smoother.update(raw_l))
        if right_valid:
            raw_r = calculate_angle(keypoints["right_hip"], keypoints["right_knee"], keypoints["right_ankle"])
            knee_angles.append(self.right_knee_smoother.update(raw_r))

        if not knee_angles:
            if are_landmarks_valid(keypoints, ["left_shoulder", "left_hip", "left_knee"]):
                knee_angles.append(self.left_knee_smoother.update(calculate_angle(keypoints["left_shoulder"], keypoints["left_hip"], keypoints["left_knee"])))
            elif are_landmarks_valid(keypoints, ["right_shoulder", "right_hip", "right_knee"]):
                knee_angles.append(self.right_knee_smoother.update(calculate_angle(keypoints["right_shoulder"], keypoints["right_hip"], keypoints["right_knee"])))

        if not knee_angles:
            return self.build_result("STANDING", feedback=["Position legs in view"], valid=False)

        avg_knee_angle = float(np.mean(knee_angles))
        feedback_list = []
        is_good_form = True
        now = time.time()

        if self.state == "STANDING":
            if avg_knee_angle <= self.squat_angle:
                self.state = "SQUAT"
                self.min_knee_angle_in_rep = avg_knee_angle
                feedback_list.append("Good squat depth! Stand up")
            else:
                feedback_list.append("Squat Down")

        elif self.state == "SQUAT":
            if avg_knee_angle < self.min_knee_angle_in_rep:
                self.min_knee_angle_in_rep = avg_knee_angle

            if avg_knee_angle >= self.standing_angle:
                if (now - self.last_rep_time) >= self.debounce_sec:
                    self.rep_count += 1
                    self.last_rep_time = now

                    if self.min_knee_angle_in_rep <= self.squat_angle:
                        feedback_list.append("Great Rep!")
                    else:
                        feedback_list.append("Squat deeper next time")
                        is_good_form = False

                    self.form_scores.append(1 if is_good_form else 0)

                self.state = "STANDING"
                self.min_knee_angle_in_rep = 180.0
            else:
                feedback_list.append("Stand Up!")

        if is_good_form and not feedback_list:
            feedback_list.append("GOOD FORM")

        return self.build_result(self.state, primary_angle=avg_knee_angle, feedback=feedback_list, valid=True)
