import time
import numpy as np
from utils import calculate_angle, AngleSmoother, BaseExerciseTracker, are_landmarks_valid

class BicycleCrunchTracker(BaseExerciseTracker):
    """
    Bicycle Crunch Tracker:
    Measures Elbow to opposite Knee contraction angle.
    States: EXTENDED (<130 deg) <-> CRUNCHED (>75 deg)
    """
    def __init__(self, crunch_angle=90.0, debounce_sec=0.3):
        super().__init__("Bicycle Crunches")
        self.crunch_angle = crunch_angle
        self.debounce_sec = debounce_sec

        self.state = "EXTENDED"
        self.last_rep_time = 0.0
        self.angle_smoother = AngleSmoother(alpha=0.35)

    def process(self, keypoints):
        left_valid = are_landmarks_valid(keypoints, ["left_elbow", "right_knee", "left_hip"])
        right_valid = are_landmarks_valid(keypoints, ["right_elbow", "left_knee", "right_hip"])

        crunch_angles = []
        if left_valid:
            crunch_angles.append(self.angle_smoother.update(calculate_angle(keypoints["left_elbow"], keypoints["left_hip"], keypoints["right_knee"])))
        if right_valid:
            crunch_angles.append(self.angle_smoother.update(calculate_angle(keypoints["right_elbow"], keypoints["right_hip"], keypoints["left_knee"])))

        if not crunch_angles:
            if are_landmarks_valid(keypoints, ["left_shoulder", "left_hip", "left_knee"]):
                crunch_angles.append(self.angle_smoother.update(calculate_angle(keypoints["left_shoulder"], keypoints["left_hip"], keypoints["left_knee"])))

        if not crunch_angles:
            return self.build_result("EXTENDED", feedback=["Position body in view"], valid=False)

        min_crunch_angle = float(np.min(crunch_angles))
        feedback_list = []
        is_good_form = True
        now = time.time()

        if self.state == "EXTENDED":
            if min_crunch_angle <= self.crunch_angle:
                self.state = "CRUNCHED"
                feedback_list.append("Elbow to knee! Switch sides")
            else:
                feedback_list.append("Bring Elbow to Opposite Knee")

        elif self.state == "CRUNCHED":
            if min_crunch_angle >= self.crunch_angle + 25.0:
                if (now - self.last_rep_time) >= self.debounce_sec:
                    self.rep_count += 1
                    self.last_rep_time = now
                    feedback_list.append("Great Bicycle Crunch!")
                    self.form_scores.append(1)

                self.state = "EXTENDED"
            else:
                feedback_list.append("Switch Sides")

        if is_good_form and not feedback_list:
            feedback_list.append("GOOD FORM")

        return self.build_result(self.state, primary_angle=min_crunch_angle, feedback=feedback_list, valid=True)
