"""
EmotiLearn AI — Adaptive Learning Engine
Dynamically adapts lesson content based on detected student emotion.
"""
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional

@dataclass
class Adaptation:
    type: str           # simplify | hint | quiz | celebrate | slow_pace | accelerate
    title: str
    description: str
    content_change: str
    priority: int       # 1=low, 3=high

RULES: Dict[str, List[Adaptation]] = {
    "confused": [
        Adaptation("simplify", "Simpler Explanation", 
                   "AI detected confusion — switching to simpler language",
                   "Show simpler_explanation field from lesson", 3),
        Adaptation("example", "More Examples",
                   "Adding step-by-step worked examples",
                   "Expand examples section with detailed steps", 2),
        Adaptation("slow_pace", "Slow Down",
                   "Reducing content density",
                   "Display content in smaller chunks", 1),
    ],
    "frustrated": [
        Adaptation("hint", "Helpful Hint",
                   "Providing targeted hint to reduce frustration",
                   "Show hint field from lesson", 3),
        Adaptation("slow_pace", "Take It Step by Step",
                   "Breaking problem into micro-steps",
                   "Show numbered step-by-step breakdown", 2),
        Adaptation("encourage", "Encouragement",
                   "Positive reinforcement message",
                   "Display encouragement banner", 1),
    ],
    "bored": [
        Adaptation("quiz", "Interactive Quiz",
                   "Boredom detected — launching quick quiz",
                   "Auto-open quiz panel", 3),
        Adaptation("gamify", "Challenge Mode",
                   "Introducing gamified element",
                   "Show bonus challenge card", 2),
        Adaptation("real_world", "Real-World Connection",
                   "Showing practical application",
                   "Display fun_fact field from lesson", 1),
    ],
    "happy": [
        Adaptation("accelerate", "Keep Momentum",
                   "Great engagement! Moving forward",
                   "Highlight next topic", 2),
        Adaptation("celebrate", "Celebrate Progress",
                   "Positive milestone reached!",
                   "Show celebration animation", 1),
    ],
    "focused": [
        Adaptation("maintain", "Stay On Track",
                   "Good focus! Continuing with lesson",
                   "No change needed", 1),
    ]
}

class AdaptiveEngine:
    def __init__(self):
        self.emotion_history: List[str] = []
        self.adaptation_count: Dict[str, int] = {}

    def get_adaptation(self, emotion: str, topic: str = "") -> dict:
        """Return the most appropriate adaptation for the detected emotion."""
        self.emotion_history.append(emotion)
        if len(self.emotion_history) > 50:
            self.emotion_history.pop(0)
        rules = RULES.get(emotion, RULES["focused"])
        # Pick highest priority rule not overused
        for rule in sorted(rules, key=lambda r: -r.priority):
            key = f"{emotion}_{rule.type}"
            count = self.adaptation_count.get(key, 0)
            if count < 3:  # Don't repeat same adaptation more than 3 times
                self.adaptation_count[key] = count + 1
                return asdict(rule) | {"emotion": emotion, "topic": topic}
        # Fallback
        return asdict(rules[0]) | {"emotion": emotion, "topic": topic}

    def get_session_summary(self) -> dict:
        """Summarize emotion distribution for a session."""
        if not self.emotion_history:
            return {}
        counts: Dict[str, int] = {}
        for e in self.emotion_history:
            counts[e] = counts.get(e, 0) + 1
        total = len(self.emotion_history)
        return {
            "distribution": {k: round(v/total*100) for k, v in counts.items()},
            "dominant_emotion": max(counts, key=counts.get),
            "total_samples": total,
            "focus_rate": round(counts.get("focused", 0) / total * 100),
        }

    def get_teacher_alert(self, student_id: str, emotion: str, duration_seconds: int) -> Optional[dict]:
        """Generate teacher alert if student is struggling too long."""
        if emotion in ("frustrated", "confused") and duration_seconds > 120:
            return {
                "studentId": student_id,
                "emotion": emotion,
                "duration": duration_seconds,
                "severity": "high" if duration_seconds > 180 else "medium",
                "message": f"Student has been {emotion} for {duration_seconds//60} min {duration_seconds%60}s",
                "action": "Consider intervening or sending a message"
            }
        return None
