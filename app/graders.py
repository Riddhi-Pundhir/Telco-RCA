"""
Graders for the Telco-RCA environment.
Each grader returns a float in [0.0, 1.0].
Graders are deterministic given the same episode trajectory.

Scoring formula:
    base_score      = 1.0 if root cause fixed / correctly diagnosed, else 0.0
    efficiency_mult = 1 - (steps_taken / max_steps)   — rewards fewer steps
    speed_bonus     = max(0, 1 - elapsed_seconds/300)  — rewards speed (MTTR)
    fp_penalty      = false_positives * 0.15           — penalises wrong restarts
    final           = clamp(base * efficiency_mult + speed_bonus * 0.2 - fp_penalty, 0, 1)
"""

from .models import TaskConfig, TASK_CONFIGS


def grade_episode(
    *,
    task_name: str,
    root_cause_fixed: bool,
    steps_taken: int,
    false_positives: int,
    elapsed_seconds: float,
    correct_diagnosis: bool = False,
) -> dict:
    """
    Unified grader. Returns a score in [0.0, 1.0] and a breakdown dict.

    The score rewards:
      - Correctness: finding the actual root cause (F1 component)
      - Efficiency:  using fewer steps (fewer unnecessary checks)
      - Speed:       faster wall-clock resolution (MTTR bonus)
      - Precision:   not sending crews to wrong locations (FP penalty)
    """
    cfg: TaskConfig = TASK_CONFIGS[task_name]

    # ── F1-style root cause accuracy ──
    # True Positive = 1 if root cause identified, else 0
    # False Positives = number of wrong restarts/diagnoses
    tp = 1.0 if (root_cause_fixed or correct_diagnosis) else 0.0
    fp = float(false_positives)

    # Precision and recall for the root cause identification
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp  # Only one root cause, so recall = 1 if found
    f1_score = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    if not (root_cause_fixed or correct_diagnosis):
        return {
            "score": 0.0,
            "reason": "Root cause not identified within episode budget.",
            "breakdown": {
                "base": 0.0,
                "f1_score": 0.0,
                "efficiency": 0.0,
                "speed_bonus": 0.0,
                "fp_penalty": min(0.8, false_positives * 0.15),
                "precision": 0.0,
                "recall": 0.0,
            },
        }

    efficiency = max(0.0, 1.0 - steps_taken / cfg.max_steps)
    speed_bonus = max(0.0, 1.0 - elapsed_seconds / 300.0)
    fp_penalty = min(0.8, false_positives * 0.15)

    # Composite score: efficiency base + MTTR speed bonus - FP penalty
    raw = efficiency + speed_bonus * 0.2 - fp_penalty
    score = round(max(0.0, min(1.0, raw)), 4)

    return {
        "score": score,
        "reason": "Root cause correctly identified.",
        "breakdown": {
            "base": 1.0,
            "f1_score": round(f1_score, 4),
            "efficiency_mult": round(efficiency, 4),
            "speed_bonus": round(speed_bonus * 0.2, 4),
            "fp_penalty": round(fp_penalty, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "steps_used": steps_taken,
            "max_steps": cfg.max_steps,
            "elapsed_seconds": round(elapsed_seconds, 2),
        },
    }


def grade_easy(trajectory: dict) -> float:
    result = grade_episode(
        task_name="easy",
        root_cause_fixed=trajectory.get("root_cause_fixed", False),
        steps_taken=trajectory.get("steps_taken", 15),
        false_positives=trajectory.get("false_positives", 0),
        elapsed_seconds=trajectory.get("elapsed_seconds", 300),
        correct_diagnosis=trajectory.get("correct_diagnosis", False),
    )
    return result["score"]


def grade_medium(trajectory: dict) -> float:
    result = grade_episode(
        task_name="medium",
        root_cause_fixed=trajectory.get("root_cause_fixed", False),
        steps_taken=trajectory.get("steps_taken", 30),
        false_positives=trajectory.get("false_positives", 0),
        elapsed_seconds=trajectory.get("elapsed_seconds", 300),
        correct_diagnosis=trajectory.get("correct_diagnosis", False),
    )
    return result["score"]


def grade_hard(trajectory: dict) -> float:
    result = grade_episode(
        task_name="hard",
        root_cause_fixed=trajectory.get("root_cause_fixed", False),
        steps_taken=trajectory.get("steps_taken", 50),
        false_positives=trajectory.get("false_positives", 0),
        elapsed_seconds=trajectory.get("elapsed_seconds", 300),
        correct_diagnosis=trajectory.get("correct_diagnosis", False),
    )
    return result["score"]
