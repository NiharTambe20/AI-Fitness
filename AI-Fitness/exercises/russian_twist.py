import time
import numpy as np
from utils import calculate_angle, AngleSmoother, BaseExerciseTracker, are_landmarks_valid

class RussianTwistTracker(BaseExerciseTracker):
    """
    Russian Twist Tracker:
    Measures Left Shoulder -> Mid Hip -> Right Wrist rotation angle.
    States: CENTER <-> TWIST_LEFT / TWIST_RIGHT
    """
    def __init__(self, twist_angle=130.0, debounce_sec=0.3):
        super().__init__("Russian Twists")
        self.twist_angle = twist_angle
        self.debounce_sec = debounce_sec

        self.state = "CENTER"
        self.last_rep_time = 0.0
        self.twist_smoother = AngleSmoother(alpha=0.35)

    def process(self, keypoints):
        valid_landmarks = ["left_shoulder", "right_shoulder", "left_wrist", "right_wrist", "left_hip"]
        if not are_landmarks_valid(keypoints, ["left_shoulder", "right_shoulder"]):
            return self.build_result("CENTER", feedback=["Position upper body in view"], valid=False)

        # Measure shoulder rotation angle relative to horizontal
        raw_twist = calculate_angle(keypoints["left_shoulder"], keypoints["right_shoulder"], keypoints.get("right_wrist", keypoints["right_shoulder"]))
        smooth_twist = self.twist_smoother.update(raw_twist)

        feedback_list = []
        is_good_form = True
        now = time.time()

        if self.state == "CENTER":
            if smooth_twist <= self.twist_angle:
                self.state = "TWIST"
                feedback_list.append("Twist complete! Return center")
            else:
                feedback_list.append("Twist Torso")

        elif self.state == "TWIST":
            if smooth_twist > self.twist_angle + 15.0:
                if (now - self.last_rep_time) >= self.debounce_sec:
                    self.rep_count += 1
                    self.last_rep_time = now
                    feedback_list.append("Great Twist!")
                    self.form_scores.append(1)

                self.state = "CENTER"
            else:
                feedback_list.append("Return Center")

        if is_good_form and not feedback_list:
            feedback_list.append("GOOD FORM")

        return self.build_result(self.state, primary_angle=smooth_twist, feedback=feedback_list, valid=True)
