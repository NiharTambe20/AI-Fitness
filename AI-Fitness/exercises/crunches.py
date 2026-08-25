import time
import numpy as np
from utils import calculate_angle, AngleSmoother, BaseExerciseTracker, are_landmarks_valid

class CrunchesTracker(BaseExerciseTracker):
    """
    Crunches Tracker:
    Measures Shoulder -> Hip -> Knee abdominal crunch contraction.
    States: DOWN (>140 deg) <-> CRUNCH (<105 deg)
    """
    def __init__(self, down_angle=140.0, crunch_angle=105.0, debounce_sec=0.4):
        super().__init__("Crunches")
        self.down_angle = down_angle
        self.crunch_angle = crunch_angle
        self.debounce_sec = debounce_sec

        self.state = "DOWN"
        self.last_rep_time = 0.0

        self.left_hip_smoother = AngleSmoother(alpha=0.35)
        self.right_hip_smoother = AngleSmoother(alpha=0.35)

    def process(self, keypoints):
        left_valid = are_landmarks_valid(keypoints, ["left_shoulder", "left_hip", "left_knee"])
        right_valid = are_landmarks_valid(keypoints, ["right_shoulder", "right_hip", "right_knee"])

        hip_angles = []
        if left_valid:
            hip_angles.append(self.left_hip_smoother.update(calculate_angle(keypoints["left_shoulder"], keypoints["left_hip"], keypoints["left_knee"])))
        if right_valid:
            hip_angles.append(self.right_hip_smoother.update(calculate_angle(keypoints["right_shoulder"], keypoints["right_hip"], keypoints["right_knee"])))

        if not hip_angles:
            return self.build_result("DOWN", feedback=["Position torso and knees in view"], valid=False)

        avg_hip_angle = float(np.mean(hip_angles))
        feedback_list = []
        is_good_form = True
        now = time.time()

        if self.state == "DOWN":
            if avg_hip_angle <= self.crunch_angle:
                self.state = "CRUNCH"
                feedback_list.append("Squeeze abs! Lower down")
            else:
                feedback_list.append("Crunch Up")

        elif self.state == "CRUNCH":
            if avg_hip_angle >= self.down_angle:
                if (now - self.last_rep_time) >= self.debounce_sec:
                    self.rep_count += 1
                    self.last_rep_time = now
                    feedback_list.append("Great Crunch!")
                    self.form_scores.append(1)

                self.state = "DOWN"
            else:
                feedback_list.append("Lower Down")

        if is_good_form and not feedback_list:
            feedback_list.append("GOOD FORM")

        return self.build_result(self.state, primary_angle=avg_hip_angle, feedback=feedback_list, valid=True)
