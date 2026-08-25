from typing import Optional, Tuple
from assistant import AIFitnessAssistant, WorkoutSessionData, UserProfile

class AIService:
    """
    Service layer bridging FastAPI backend requests with Member 4 AIFitnessAssistant.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.assistant = AIFitnessAssistant(api_key=api_key)

    def generate_coaching_for_session(
        self,
        session_data: WorkoutSessionData,
        user_profile: Optional[UserProfile] = None
    ) -> Tuple[str, str]:
        """
        Generates AI workout coaching feedback and identifies the provider used.
        Returns: (feedback_text, provider_name)
        """
        feedback_text = self.assistant.generate_workout_feedback(session_data, user_profile)
        provider = "Gemini" if self.assistant.genai_client is not None else "Offline/Rule-Based"
        return feedback_text, provider

    def explain_form_issues(self, exercise_name: str, form_score: float, feedback_events: list) -> str:
        return self.assistant.explain_form_issues(exercise_name, form_score, feedback_events)

    def answer_fitness_question(self, question: str, user_profile: Optional[UserProfile] = None) -> str:
        return self.assistant.answer_fitness_question(question, user_profile)

ai_service = AIService()
