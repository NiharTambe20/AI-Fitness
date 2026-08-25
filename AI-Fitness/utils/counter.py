class BaseExerciseTracker:
    """
    Base interface for all exercise trackers in the AI Fitness system.
    """
    def __init__(self, name):
        self.name = name
        self.rep_count = 0
        self.form_scores = []  # Stores 1 for good form, 0 for poor form
        self.feedback_events = []  # Stores unique feedback messages across the session

    def process(self, keypoints):
        """
        Input: keypoints dict
        Output: Standard dictionary with exercise, rep_count, state, primary_angle, secondary_angle, form_score, feedback, valid
        """
        raise NotImplementedError

    def get_form_score(self):
        if not self.form_scores or self.rep_count == 0:
            return 0.0
        return round((sum(self.form_scores) / len(self.form_scores)) * 100.0, 1)

    def build_result(self, state, primary_angle=None, secondary_angle=None, feedback=None, valid=True):
        fb = feedback if feedback is not None else ["GOOD FORM"]
        ignore_list = ["GOOD FORM", "Position arms in view", "Position legs in view", "Position body in view"]
        for msg in fb:
            if msg not in ignore_list and msg not in self.feedback_events:
                self.feedback_events.append(msg)

        return {
            "exercise": self.name,
            "rep_count": self.rep_count,
            "state": state,
            "primary_angle": round(primary_angle, 1) if primary_angle is not None else None,
            "secondary_angle": round(secondary_angle, 1) if secondary_angle is not None else None,
            "form_score": self.get_form_score(),
            "feedback": fb,
            "valid": valid
        }
