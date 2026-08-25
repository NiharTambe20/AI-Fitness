import time
import numpy as np
from utils import calculate_angle, AngleSmoother, BaseExerciseTracker, are_landmarks_valid

class MountainClimbersTracker(BaseExerciseTracker):
    """
    Mountain Climbers Tracker:
    Measures Shoulder -> Hip -> Knee angle during horizontal plank drive.
    States: PLANK (>135 deg) <-> DRIVE (<90 deg)
    """
    def __init__(self, plank_angle=135.0, drive_angle=90.0, debounce_sec=0.3):
        super().__init__("Mountain Climbers")
        self.plank_angle = plank_angle
        self.drive_angle = drive_angle
        self.debounce_sec = debounce_sec

        self.state = "PLANK"
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
            return self.build_result("PLANK", feedback=["Position body in view"], valid=False)

        min_hip_angle = float(np.min(hip_angles))
        feedback_list = []
        is_good_form = True
        now = time.time()

        if self.state == "PLANK":
            if min_hip_angle <= self.drive_angle:
                self.state = "DRIVE"
                feedback_list.append("Good knee drive!")
            else:
                feedback_list.append("Drive Knee Forward")

        elif self.state == "DRIVE":
            if min_hip_angle >= self.plank_angle:
                if (now - self.last_rep_time) >= self.debounce_sec:
                    self.rep_count += 1
                    self.last_rep_time = now
                    feedback_list.append("Great Drive!")
                    self.form_scores.append(1)

                self.state = "PLANK"
            else:
                feedback_list.append("Extend Leg Back")

        if is_good_form and not feedback_list:
            feedback_list.append("GOOD FORM")

        return self.build_result(self.state, primary_angle=min_hip_angle, feedback=feedback_list, valid=True)
