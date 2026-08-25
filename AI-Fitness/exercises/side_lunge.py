import time
import numpy as np
from utils import calculate_angle, AngleSmoother, BaseExerciseTracker, are_landmarks_valid

class SideLungeTracker(BaseExerciseTracker):
    """
    Side Lunge Tracker:
    Measures lateral Hip -> Knee -> Ankle bend angle.
    States: STANDING (>155 deg) <-> SIDE_LUNGE (<115 deg)
    """
    def __init__(self, standing_angle=155.0, lunge_angle=115.0, debounce_sec=0.4):
        super().__init__("Side Lunges")
        self.standing_angle = standing_angle
        self.lunge_angle = lunge_angle
        self.debounce_sec = debounce_sec

        self.state = "STANDING"
        self.last_rep_time = 0.0

        self.knee_smoother = AngleSmoother(alpha=0.35)

    def process(self, keypoints):
        left_valid = are_landmarks_valid(keypoints, ["left_hip", "left_knee", "left_ankle"])
        right_valid = are_landmarks_valid(keypoints, ["right_hip", "right_knee", "right_ankle"])

        knee_angles = []
        if left_valid:
            knee_angles.append(self.knee_smoother.update(calculate_angle(keypoints["left_hip"], keypoints["left_knee"], keypoints["left_ankle"])))
        if right_valid:
            knee_angles.append(self.knee_smoother.update(calculate_angle(keypoints["right_hip"], keypoints["right_knee"], keypoints["right_ankle"])))

        if not knee_angles:
            return self.build_result("STANDING", feedback=["Position legs in view"], valid=False)

        min_knee_angle = float(np.min(knee_angles))
        feedback_list = []
        is_good_form = True
        now = time.time()

        if self.state == "STANDING":
            if min_knee_angle <= self.lunge_angle:
                self.state = "SIDE_LUNGE"
                feedback_list.append("Good side lunge! Push back center")
            else:
                feedback_list.append("Step Sideways into Lunge")

        elif self.state == "SIDE_LUNGE":
            if min_knee_angle >= self.standing_angle:
                if (now - self.last_rep_time) >= self.debounce_sec:
                    self.rep_count += 1
                    self.last_rep_time = now
                    feedback_list.append("Great Side Lunge!")
                    self.form_scores.append(1)

                self.state = "STANDING"
            else:
                feedback_list.append("Return Center")

        if is_good_form and not feedback_list:
            feedback_list.append("GOOD FORM")

        return self.build_result(self.state, primary_angle=min_knee_angle, feedback=feedback_list, valid=True)
