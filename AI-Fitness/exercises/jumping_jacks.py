import time
import numpy as np
from utils import calculate_angle, AngleSmoother, BaseExerciseTracker, are_landmarks_valid

class JumpingJacksTracker(BaseExerciseTracker):
    """
    Jumping Jacks Tracker:
    Measures Hip -> Shoulder -> Wrist overhead arm angle.
    States: CLOSED (<60 deg) <-> OPEN (>135 deg)
    """
    def __init__(self, closed_angle=60.0, open_angle=135.0, debounce_sec=0.3):
        super().__init__("Jumping Jacks")
        self.closed_angle = closed_angle
        self.open_angle = open_angle
        self.debounce_sec = debounce_sec

        self.state = "CLOSED"
        self.last_rep_time = 0.0

        self.left_arm_smoother = AngleSmoother(alpha=0.35)
        self.right_arm_smoother = AngleSmoother(alpha=0.35)

    def process(self, keypoints):
        left_valid = are_landmarks_valid(keypoints, ["left_hip", "left_shoulder", "left_wrist"])
        right_valid = are_landmarks_valid(keypoints, ["right_hip", "right_shoulder", "right_wrist"])

        arm_angles = []
        if left_valid:
            arm_angles.append(self.left_arm_smoother.update(calculate_angle(keypoints["left_hip"], keypoints["left_shoulder"], keypoints["left_wrist"])))
        if right_valid:
            arm_angles.append(self.right_arm_smoother.update(calculate_angle(keypoints["right_hip"], keypoints["right_shoulder"], keypoints["right_wrist"])))

        if not arm_angles:
            return self.build_result("CLOSED", feedback=["Position upper body in view"], valid=False)

        avg_arm_angle = float(np.mean(arm_angles))
        feedback_list = []
        is_good_form = True
        now = time.time()

        if self.state == "CLOSED":
            if avg_arm_angle >= self.open_angle:
                self.state = "OPEN"
                feedback_list.append("Open! Jump back in")
            else:
                feedback_list.append("Jump Out")

        elif self.state == "OPEN":
            if avg_arm_angle <= self.closed_angle:
                if (now - self.last_rep_time) >= self.debounce_sec:
                    self.rep_count += 1
                    self.last_rep_time = now
                    feedback_list.append("Great Jack!")
                    self.form_scores.append(1)

                self.state = "CLOSED"
            else:
                feedback_list.append("Jump In")

        if is_good_form and not feedback_list:
            feedback_list.append("GOOD FORM")

        return self.build_result(self.state, primary_angle=avg_arm_angle, feedback=feedback_list, valid=True)
