import time
import numpy as np
from utils import calculate_angle, AngleSmoother, BaseExerciseTracker, are_landmarks_valid

class ShoulderPressTracker(BaseExerciseTracker):
    """
    Shoulder Press Tracker:
    Measures Hip -> Shoulder -> Wrist OR Elbow -> Shoulder -> Wrist angle overhead.
    States: LOWERED (<105 deg) <-> PRESSED (>150 deg)
    """
    def __init__(self, lowered_angle=105.0, pressed_angle=150.0, debounce_sec=0.4):
        super().__init__("Shoulder Press")
        self.lowered_angle = lowered_angle
        self.pressed_angle = pressed_angle
        self.debounce_sec = debounce_sec

        self.state = "LOWERED"
        self.last_rep_time = 0.0

        self.left_arm_smoother = AngleSmoother(alpha=0.35)
        self.right_arm_smoother = AngleSmoother(alpha=0.35)
        self.max_angle_in_rep = 0.0

    def process(self, keypoints):
        left_valid = are_landmarks_valid(keypoints, ["left_hip", "left_shoulder", "left_wrist"])
        right_valid = are_landmarks_valid(keypoints, ["right_hip", "right_shoulder", "right_wrist"])

        arm_angles = []
        if left_valid:
            arm_angles.append(self.left_arm_smoother.update(calculate_angle(keypoints["left_hip"], keypoints["left_shoulder"], keypoints["left_wrist"])))
        if right_valid:
            arm_angles.append(self.right_arm_smoother.update(calculate_angle(keypoints["right_hip"], keypoints["right_shoulder"], keypoints["right_wrist"])))

        if not arm_angles:
            if are_landmarks_valid(keypoints, ["left_shoulder", "left_elbow", "left_wrist"]):
                arm_angles.append(self.left_arm_smoother.update(calculate_angle(keypoints["left_shoulder"], keypoints["left_elbow"], keypoints["left_wrist"])))
            elif are_landmarks_valid(keypoints, ["right_shoulder", "right_elbow", "right_wrist"]):
                arm_angles.append(self.right_arm_smoother.update(calculate_angle(keypoints["right_shoulder"], keypoints["right_elbow"], keypoints["right_wrist"])))

        if not arm_angles:
            return self.build_result("LOWERED", feedback=["Position upper body in view"], valid=False)

        avg_arm_angle = float(np.mean(arm_angles))
        feedback_list = []
        is_good_form = True
        now = time.time()

        if self.state == "LOWERED":
            if avg_arm_angle >= self.pressed_angle:
                self.state = "PRESSED"
                self.max_angle_in_rep = avg_arm_angle
                feedback_list.append("Full extension! Lower arms")
            else:
                feedback_list.append("Press Overhead")

        elif self.state == "PRESSED":
            if avg_arm_angle > self.max_angle_in_rep:
                self.max_angle_in_rep = avg_arm_angle

            if avg_arm_angle <= self.lowered_angle:
                if (now - self.last_rep_time) >= self.debounce_sec:
                    self.rep_count += 1
                    self.last_rep_time = now

                    if self.max_angle_in_rep >= self.pressed_angle:
                        feedback_list.append("Great Press!")
                    else:
                        feedback_list.append("Extend higher next time")
                        is_good_form = False

                    self.form_scores.append(1 if is_good_form else 0)

                self.state = "LOWERED"
                self.max_angle_in_rep = 0.0
            else:
                feedback_list.append("Lower Arms")

        if is_good_form and not feedback_list:
            feedback_list.append("GOOD FORM")

        return self.build_result(self.state, primary_angle=avg_arm_angle, feedback=feedback_list, valid=True)
