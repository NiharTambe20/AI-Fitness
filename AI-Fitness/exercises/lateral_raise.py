import time
import numpy as np
from utils import calculate_angle, AngleSmoother, BaseExerciseTracker, are_landmarks_valid

class LateralRaiseTracker(BaseExerciseTracker):
    """
    Lateral Raise Tracker:
    Measures Hip -> Shoulder -> Wrist side arm elevation angle.
    States: LOWERED (<35 deg) <-> RAISED (>80 deg)
    """
    def __init__(self, lowered_angle=35.0, raised_angle=80.0, debounce_sec=0.4):
        super().__init__("Lateral Raises")
        self.lowered_angle = lowered_angle
        self.raised_angle = raised_angle
        self.debounce_sec = debounce_sec

        self.state = "LOWERED"
        self.last_rep_time = 0.0

        self.arm_smoother = AngleSmoother(alpha=0.35)

    def process(self, keypoints):
        left_valid = are_landmarks_valid(keypoints, ["left_hip", "left_shoulder", "left_wrist"])
        right_valid = are_landmarks_valid(keypoints, ["right_hip", "right_shoulder", "right_wrist"])

        arm_angles = []
        if left_valid:
            arm_angles.append(self.arm_smoother.update(calculate_angle(keypoints["left_hip"], keypoints["left_shoulder"], keypoints["left_wrist"])))
        if right_valid:
            arm_angles.append(self.arm_smoother.update(calculate_angle(keypoints["right_hip"], keypoints["right_shoulder"], keypoints["right_wrist"])))

        if not arm_angles:
            return self.build_result("LOWERED", feedback=["Position arms in view"], valid=False)

        avg_arm_angle = float(np.mean(arm_angles))
        feedback_list = []
        is_good_form = True
        now = time.time()

        if self.state == "LOWERED":
            if avg_arm_angle >= self.raised_angle:
                self.state = "RAISED"
                feedback_list.append("Parallel to floor! Lower arms")
            else:
                feedback_list.append("Raise Arms Sideways")

        elif self.state == "RAISED":
            if avg_arm_angle <= self.lowered_angle:
                if (now - self.last_rep_time) >= self.debounce_sec:
                    self.rep_count += 1
                    self.last_rep_time = now
                    feedback_list.append("Great Lateral Raise!")
                    self.form_scores.append(1)

                self.state = "LOWERED"
            else:
                feedback_list.append("Lower Arms")

        if is_good_form and not feedback_list:
            feedback_list.append("GOOD FORM")

        return self.build_result(self.state, primary_angle=avg_arm_angle, feedback=feedback_list, valid=True)
