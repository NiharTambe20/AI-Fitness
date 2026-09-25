import time
import math
import pytest
from exercises.bicep_curl import BicepCurlTracker

def make_arm_keypoints(left_angle=None, right_angle=None, left_drift=False, right_drift=False):
    """
    Helper to construct keypoints for left and/or right arm with given elbow angles.
    Shoulder is at (200, 100), elbow at (200, 200).
    Wrist is positioned based on the desired angle.
    """
    kpts = {}
    if left_angle is not None:
        # Left arm
        sh_x = 100
        el_x = 200 if left_drift else 100  # if left_drift, dx = 100 > 80
        kpts["left_shoulder"] = {"x": sh_x, "y": 100, "conf": 0.9, "valid": True}
        kpts["left_elbow"] = {"x": el_x, "y": 200, "conf": 0.9, "valid": True}
        # angle between (sh - el) and (wr - el)
        # sh is (sh_x, 100), el is (el_x, 200) -> vector el->sh is roughly (0, -100)
        # angle 180 means straight down (0, 100). angle 45 means pointing up toward shoulder.
        rad = math.radians(180.0 - left_angle)
        wr_x = el_x + int(math.sin(rad) * 100)
        wr_y = 200 + int(math.cos(rad) * 100)
        kpts["left_wrist"] = {"x": wr_x, "y": wr_y, "conf": 0.9, "valid": True}

    if right_angle is not None:
        # Right arm
        sh_x = 300
        el_x = 400 if right_drift else 300
        kpts["right_shoulder"] = {"x": sh_x, "y": 100, "conf": 0.9, "valid": True}
        kpts["right_elbow"] = {"x": el_x, "y": 200, "conf": 0.9, "valid": True}
        rad = math.radians(180.0 - right_angle)
        wr_x = el_x + int(math.sin(rad) * 100)
        wr_y = 200 + int(math.cos(rad) * 100)
        kpts["right_wrist"] = {"x": wr_x, "y": wr_y, "conf": 0.9, "valid": True}

    return kpts


class TestBicepCurlRepCounting:
    """
    Focused regression test suite for Bicep Curl rep counting, independent arm tracking,
    and schema stability.
    """

    def test_single_left_arm_curl_and_extension(self):
        """1. A single visible arm (left) can enter CURLED and returning to EXTENDED increments rep count."""
        tracker = BicepCurlTracker(debounce_sec=0.1)

        # Extended position (~160 deg) for left arm only, right arm missing
        kpts_ext = make_arm_keypoints(left_angle=160.0)
        for _ in range(5):
            res = tracker.process(kpts_ext)
        assert tracker.state == "EXTENDED"
        assert tracker.rep_count == 0

        # Curled position (~60 deg <= 80.0 deg)
        kpts_curl = make_arm_keypoints(left_angle=60.0)
        for _ in range(5):
            res = tracker.process(kpts_curl)
        assert tracker.state == "CURLED"
        assert tracker.rep_count == 0

        time.sleep(0.12)  # Exceed debounce

        # Return to Extended position (~155 deg >= 140.0 deg)
        for _ in range(5):
            res = tracker.process(kpts_ext)
        assert tracker.state == "EXTENDED"
        assert tracker.rep_count == 1
        assert tracker.get_form_score() == 100.0

    def test_single_right_arm_curl_and_extension(self):
        """1b. A single visible arm (right) can enter CURLED and returning to EXTENDED increments rep count."""
        tracker = BicepCurlTracker(debounce_sec=0.1)

        kpts_ext = make_arm_keypoints(right_angle=165.0)
        for _ in range(5):
            tracker.process(kpts_ext)
        assert tracker.state == "EXTENDED"

        kpts_curl = make_arm_keypoints(right_angle=55.0)
        for _ in range(5):
            tracker.process(kpts_curl)
        assert tracker.state == "CURLED"

        time.sleep(0.12)

        for _ in range(5):
            tracker.process(kpts_ext)
        assert tracker.state == "EXTENDED"
        assert tracker.rep_count == 1

    def test_alternating_curls_increment_reps(self):
        """3. Alternating single-arm curls increment reps properly without being blocked by resting arm."""
        tracker = BicepCurlTracker(debounce_sec=0.1)

        # Start with both arms extended (160 deg)
        kpts_both_ext = make_arm_keypoints(left_angle=160.0, right_angle=160.0)
        for _ in range(5):
            tracker.process(kpts_both_ext)
        assert tracker.state == "EXTENDED"
        assert tracker.rep_count == 0

        # Rep 1: Left arm curls (55 deg), Right arm stays resting extended (160 deg)
        kpts_left_curl = make_arm_keypoints(left_angle=55.0, right_angle=160.0)
        for _ in range(5):
            tracker.process(kpts_left_curl)
        assert tracker.state == "CURLED"

        time.sleep(0.12)

        # Left arm lowers back to extended (155 deg), Right arm still resting (160 deg)
        for _ in range(5):
            tracker.process(kpts_both_ext)
        assert tracker.state == "EXTENDED"
        assert tracker.rep_count == 1

        time.sleep(0.12)

        # Rep 2: Right arm curls (50 deg), Left arm stays resting extended (160 deg)
        kpts_right_curl = make_arm_keypoints(left_angle=160.0, right_angle=50.0)
        for _ in range(5):
            tracker.process(kpts_right_curl)
        assert tracker.state == "CURLED"

        time.sleep(0.12)

        # Right arm lowers back to extended (155 deg)
        for _ in range(5):
            tracker.process(kpts_both_ext)
        assert tracker.state == "EXTENDED"
        assert tracker.rep_count == 2

    def test_missing_one_arm_does_not_prevent_other_arm_evaluation(self):
        """4. Missing one arm keypoints completely does not prevent the valid arm from counting reps."""
        tracker = BicepCurlTracker(debounce_sec=0.1)

        # Left arm present, right arm keypoints not even in dictionary
        kpts_ext = {"left_shoulder": {"x": 100, "y": 100, "conf": 0.9, "valid": True},
                    "left_elbow": {"x": 100, "y": 200, "conf": 0.9, "valid": True},
                    "left_wrist": {"x": 100, "y": 300, "conf": 0.9, "valid": True}}
        for _ in range(5):
            res = tracker.process(kpts_ext)
        assert res["valid"] is True
        assert tracker.state == "EXTENDED"

        kpts_curl = {"left_shoulder": {"x": 100, "y": 100, "conf": 0.9, "valid": True},
                     "left_elbow": {"x": 100, "y": 200, "conf": 0.9, "valid": True},
                     "left_wrist": {"x": 100, "y": 130, "conf": 0.9, "valid": True}}
        for _ in range(5):
            res = tracker.process(kpts_curl)
        assert res["valid"] is True
        assert tracker.state == "CURLED"

        time.sleep(0.12)

        for _ in range(5):
            res = tracker.process(kpts_ext)
        assert tracker.state == "EXTENDED"
        assert tracker.rep_count == 1

    def test_bilateral_curl_both_arms(self):
        """Bilateral curl with both arms curling and extending simultaneously."""
        tracker = BicepCurlTracker(debounce_sec=0.1)
        kpts_ext = make_arm_keypoints(left_angle=160.0, right_angle=160.0)
        kpts_curl = make_arm_keypoints(left_angle=65.0, right_angle=65.0)

        for _ in range(5): tracker.process(kpts_ext)
        for _ in range(5): tracker.process(kpts_curl)
        assert tracker.state == "CURLED"

        time.sleep(0.12)
        for _ in range(5): tracker.process(kpts_ext)
        assert tracker.state == "EXTENDED"
        assert tracker.rep_count == 1

    def test_response_schema_fields_unchanged(self):
        """5. Existing response fields remain unchanged and match expected schema."""
        tracker = BicepCurlTracker()
        kpts = make_arm_keypoints(left_angle=150.0, right_angle=150.0)
        res = tracker.process(kpts)

        expected_fields = [
            "exercise",
            "rep_count",
            "state",
            "primary_angle",
            "secondary_angle",
            "form_score",
            "feedback",
            "valid",
            "feedback_code",
            "feedback_detail",
            "feedback_priority",
        ]
        for field in expected_fields:
            assert field in res, f"Field '{field}' missing from tracker response"

        assert res["exercise"] == "Bicep Curl"
        assert res["valid"] is True
        assert isinstance(res["feedback"], list)
        assert isinstance(res["rep_count"], int)
        assert isinstance(res["primary_angle"], float)

    def test_landmarks_missing_response_structure(self):
        """When landmarks are missing, returns proper LANDMARKS_MISSING code and detail."""
        tracker = BicepCurlTracker()
        res = tracker.process({})
        assert res["valid"] is False
        assert res["feedback_code"] == "LANDMARKS_MISSING"
        assert "Position your arms and upper body clearly in camera view." in res["feedback_detail"]
        assert res["feedback_priority"] == 1

    def test_curled_threshold_80_degrees(self):
        """Verifies new threshold curled_angle = 80.0 allows curls at 75 deg to trigger CURLED."""
        tracker = BicepCurlTracker()
        kpts_ext = make_arm_keypoints(left_angle=150.0)
        for _ in range(5): tracker.process(kpts_ext)

        # 75 deg would have failed old 65.0 threshold, now passes 80.0 threshold
        kpts_curl_75 = make_arm_keypoints(left_angle=75.0)
        for _ in range(5): res = tracker.process(kpts_curl_75)
        assert tracker.state == "CURLED"

    def test_extended_threshold_140_degrees(self):
        """Verifies new threshold extended_angle = 140.0 allows extension at 142 deg to complete rep."""
        tracker = BicepCurlTracker(debounce_sec=0.1)
        kpts_ext = make_arm_keypoints(left_angle=150.0)
        for _ in range(5): tracker.process(kpts_ext)

        kpts_curl = make_arm_keypoints(left_angle=60.0)
        for _ in range(5): tracker.process(kpts_curl)
        assert tracker.state == "CURLED"

        time.sleep(0.12)
        # 142 deg would have failed old 145.0 threshold, now passes 140.0 threshold
        kpts_ext_142 = make_arm_keypoints(left_angle=142.0)
        for _ in range(5): tracker.process(kpts_ext_142)
        assert tracker.state == "EXTENDED"
        assert tracker.rep_count == 1
