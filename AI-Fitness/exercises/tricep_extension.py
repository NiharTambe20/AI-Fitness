import time
import numpy as np
from utils import calculate_angle, AngleSmoother, BaseExerciseTracker, are_landmarks_valid

class TricepExtensionTracker(BaseExerciseTracker):
    """
    Tricep Extension Tracker:
    Measures Shoulder -> Elbow -> Wrist overhead arm extension angle.
    States: BENT (<75 deg) <-> EXTENDED (>150 deg)
    """
    def __init__(self, bent_angle=75.0, extended_angle=150.0, debounce_sec=0.4):
        super().__init__("Tricep Extensions")
        self.bent_angle = bent_angle
        self.extended_angle = extended_angle
        self.debounce_sec = debounce_sec

        self.state = "BENT"
        self.last_rep_time = 0.0

        self.left_elbow_smoother = AngleSmoother(alpha=0.35)
        self.right_elbow_smoother = AngleSmoother(alpha=0.35)

    def process(self, keypoints):
        left_valid = are_landmarks_valid(keypoints, ["left_shoulder", "left_elbow", "left_wrist"])
        right_valid = are_landmarks_valid(keypoints, ["right_shoulder", "right_elbow", "right_wrist"])

        elbow_angles = []
        if left_valid:
            elbow_angles.append(self.left_elbow_smoother.update(calculate_angle(keypoints["left_shoulder"], keypoints["left_elbow"], keypoints["left_wrist"])))
        if right_valid:
            elbow_angles.append(self.right_elbow_smoother.update(calculate_angle(keypoints["right_shoulder"], keypoints["right_elbow"], keypoints["right_wrist"])))

        if not elbow_angles:
            return self.build_result("BENT", feedback=["Position arms overhead in view"], valid=False)

        avg_elbow_angle = float(np.mean(elbow_angles))
        feedback_list = []
        is_good_form = True
        now = time.time()

        if self.state == "BENT":
            if avg_elbow_angle >= self.extended_angle:
                self.state = "EXTENDED"
                feedback_list.append("Full extension! Lower weights behind head")
            else:
                feedback_list.append("Extend Arms Overhead")

        elif self.state == "EXTENDED":
            if avg_elbow_angle <= self.bent_angle:
                if (now - self.last_rep_time) >= self.debounce_sec:
                    self.rep_count += 1
                    self.last_rep_time = now
                    feedback_list.append("Great Tricep Extension!")
                    self.form_scores.append(1)

                self.state = "BENT"
            else:
                feedback_list.append("Lower Behind Head")

        if is_good_form and not feedback_list:
            feedback_list.append("GOOD FORM")

        return self.build_result(self.state, primary_angle=avg_elbow_angle, feedback=feedback_list, valid=True)
