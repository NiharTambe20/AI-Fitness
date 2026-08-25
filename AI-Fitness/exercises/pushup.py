import time
import numpy as np
from utils import calculate_angle, AngleSmoother, BaseExerciseTracker, are_landmarks_valid

class PushUpTracker(BaseExerciseTracker):
    """
    Push-Up Repetition Tracker & Form Evaluator.
    States: UP (>150 deg) <-> DOWN (<110 deg)
    """
    def __init__(self, up_angle=150.0, down_angle=110.0, debounce_sec=0.4):
        super().__init__("Push-up")
        self.up_angle = up_angle
        self.down_angle = down_angle
        self.debounce_sec = debounce_sec

        self.state = "UP"
        self.last_rep_time = 0.0

        self.left_elbow_smoother = AngleSmoother(alpha=0.35)
        self.right_elbow_smoother = AngleSmoother(alpha=0.35)
        self.body_line_smoother = AngleSmoother(alpha=0.35)

        self.min_elbow_angle_in_rep = 180.0

    def process(self, keypoints):
        left_valid = are_landmarks_valid(keypoints, ["left_shoulder", "left_elbow", "left_wrist"])
        right_valid = are_landmarks_valid(keypoints, ["right_shoulder", "right_elbow", "right_wrist"])

        elbow_angles = []
        if left_valid:
            raw_l = calculate_angle(keypoints["left_shoulder"], keypoints["left_elbow"], keypoints["left_wrist"])
            elbow_angles.append(self.left_elbow_smoother.update(raw_l))
        if right_valid:
            raw_r = calculate_angle(keypoints["right_shoulder"], keypoints["right_elbow"], keypoints["right_wrist"])
            elbow_angles.append(self.right_elbow_smoother.update(raw_r))

        if not elbow_angles:
            if are_landmarks_valid(keypoints, ["left_shoulder", "left_elbow", "left_hip"]):
                elbow_angles.append(self.left_elbow_smoother.update(calculate_angle(keypoints["left_hip"], keypoints["left_shoulder"], keypoints["left_elbow"])))
            elif are_landmarks_valid(keypoints, ["right_shoulder", "right_elbow", "right_hip"]):
                elbow_angles.append(self.right_elbow_smoother.update(calculate_angle(keypoints["right_hip"], keypoints["right_shoulder"], keypoints["right_elbow"])))

        if not elbow_angles:
            return self.build_result("UP", feedback=["Position upper body in view"], valid=False)

        avg_elbow_angle = float(np.mean(elbow_angles))

        body_angle = None
        if are_landmarks_valid(keypoints, ["left_shoulder", "left_hip", "left_knee"]):
            body_angle = self.body_line_smoother.update(calculate_angle(keypoints["left_shoulder"], keypoints["left_hip"], keypoints["left_knee"]))
        elif are_landmarks_valid(keypoints, ["right_shoulder", "right_hip", "right_knee"]):
            body_angle = self.body_line_smoother.update(calculate_angle(keypoints["right_shoulder"], keypoints["right_hip"], keypoints["right_knee"]))

        feedback_list = []
        is_good_form = True

        if body_angle is not None and body_angle < 140.0:
            feedback_list.append("Keep back straight")
            is_good_form = False

        now = time.time()

        if self.state == "UP":
            if avg_elbow_angle <= self.down_angle:
                self.state = "DOWN"
                self.min_elbow_angle_in_rep = avg_elbow_angle
                feedback_list.append("Good depth! Push up")
            else:
                feedback_list.append("Push Down")

        elif self.state == "DOWN":
            if avg_elbow_angle < self.min_elbow_angle_in_rep:
                self.min_elbow_angle_in_rep = avg_elbow_angle

            if avg_elbow_angle >= self.up_angle:
                if (now - self.last_rep_time) >= self.debounce_sec:
                    self.rep_count += 1
                    self.last_rep_time = now

                    if self.min_elbow_angle_in_rep <= self.down_angle:
                        feedback_list.append("Great Rep!")
                    else:
                        feedback_list.append("Go lower next time")
                        is_good_form = False

                    self.form_scores.append(1 if is_good_form else 0)

                self.state = "UP"
                self.min_elbow_angle_in_rep = 180.0
            else:
                feedback_list.append("Push Up!")

        if is_good_form and not feedback_list:
            feedback_list.append("GOOD FORM")

        return self.build_result(self.state, primary_angle=avg_elbow_angle, secondary_angle=body_angle, feedback=feedback_list, valid=True)
