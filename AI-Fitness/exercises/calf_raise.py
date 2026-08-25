import time
import numpy as np
from utils import calculate_angle, AngleSmoother, BaseExerciseTracker, are_landmarks_valid

class CalfRaiseTracker(BaseExerciseTracker):
    """
    Calf Raise Tracker:
    Measures Knee -> Ankle -> Foot angle / vertical lift.
    States: FLAT (>150 deg) <-> RAISED (<130 deg)
    """
    def __init__(self, flat_angle=150.0, raised_angle=130.0, debounce_sec=0.4):
        super().__init__("Calf Raises")
        self.flat_angle = flat_angle
        self.raised_angle = raised_angle
        self.debounce_sec = debounce_sec

        self.state = "FLAT"
        self.last_rep_time = 0.0

        self.ankle_smoother = AngleSmoother(alpha=0.35)

    def process(self, keypoints):
        left_valid = are_landmarks_valid(keypoints, ["left_knee", "left_ankle"])
        right_valid = are_landmarks_valid(keypoints, ["right_knee", "right_ankle"])

        if not left_valid and not right_valid:
            return self.build_result("FLAT", feedback=["Position lower legs in view"], valid=False)

        # Measure ankle elevation angle relative to knee line
        left_y = keypoints.get("left_ankle", {}).get("y", 0)
        right_y = keypoints.get("right_ankle", {}).get("y", 0)
        
        raw_angle = 140.0
        if left_valid:
            raw_angle = calculate_angle(keypoints.get("left_hip", keypoints["left_knee"]), keypoints["left_knee"], keypoints["left_ankle"])

        smooth_angle = self.ankle_smoother.update(raw_angle)
        feedback_list = []
        is_good_form = True
        now = time.time()

        if self.state == "FLAT":
            if smooth_angle <= self.raised_angle:
                self.state = "RAISED"
                feedback_list.append("Peak contraction! Lower heels")
            else:
                feedback_list.append("Raise Heels High")

        elif self.state == "RAISED":
            if smooth_angle >= self.flat_angle:
                if (now - self.last_rep_time) >= self.debounce_sec:
                    self.rep_count += 1
                    self.last_rep_time = now
                    feedback_list.append("Great Calf Raise!")
                    self.form_scores.append(1)

                self.state = "FLAT"
            else:
                feedback_list.append("Lower Heels")

        if is_good_form and not feedback_list:
            feedback_list.append("GOOD FORM")

        return self.build_result(self.state, primary_angle=smooth_angle, feedback=feedback_list, valid=True)
