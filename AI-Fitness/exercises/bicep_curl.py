import time
import numpy as np
from utils import calculate_angle, AngleSmoother, BaseExerciseTracker, are_landmarks_valid

class BicepCurlTracker(BaseExerciseTracker):
    """
    Bicep Curl Tracker:
    Measures Shoulder -> Elbow -> Wrist angle.
    States: EXTENDED (>145 deg) <-> CURLED (<65 deg)
    """
    def __init__(self, extended_angle=145.0, curled_angle=65.0, debounce_sec=0.4):
        super().__init__("Bicep Curl")
        self.extended_angle = extended_angle
        self.curled_angle = curled_angle
        self.debounce_sec = debounce_sec

        self.state = "EXTENDED"
        self.last_rep_time = 0.0

        self.left_elbow_smoother = AngleSmoother(alpha=0.35)
        self.right_elbow_smoother = AngleSmoother(alpha=0.35)
        self.min_angle_in_rep = 180.0

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
            return self.build_result("EXTENDED", feedback=["Position arms in view"], valid=False)

        avg_elbow_angle = float(np.mean(elbow_angles))
        feedback_list = []
        is_good_form = True
        now = time.time()

        if self.state == "EXTENDED":
            if avg_elbow_angle <= self.curled_angle:
                self.state = "CURLED"
                self.min_angle_in_rep = avg_elbow_angle
                feedback_list.append("Good curl! Lower arms")
            else:
                feedback_list.append("Curl Up")

        elif self.state == "CURLED":
            if avg_elbow_angle < self.min_angle_in_rep:
                self.min_angle_in_rep = avg_elbow_angle

            if avg_elbow_angle >= self.extended_angle:
                if (now - self.last_rep_time) >= self.debounce_sec:
                    self.rep_count += 1
                    self.last_rep_time = now

                    if self.min_angle_in_rep <= self.curled_angle:
                        feedback_list.append("Great Rep!")
                    else:
                        feedback_list.append("Curl higher next time")
                        is_good_form = False

                    self.form_scores.append(1 if is_good_form else 0)

                self.state = "EXTENDED"
                self.min_angle_in_rep = 180.0
            else:
                feedback_list.append("Lower Arms")

        if is_good_form and not feedback_list:
            feedback_list.append("GOOD FORM")

        return self.build_result(self.state, primary_angle=avg_elbow_angle, feedback=feedback_list, valid=True)
