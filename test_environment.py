"""
Basic tests for Telco-RCA environment and graders.
Run: python -m pytest tests/ -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.environment import TelcoRCAEnvironment
from app.models import AgentAction
from app.graders import grade_easy, grade_medium, grade_hard, grade_episode


class TestEnvironmentReset:
    def test_reset_returns_observation(self):
        env = TelcoRCAEnvironment("easy")
        obs = env.reset()
        assert obs.total_alarm_count >= 0
        assert obs.steps_remaining == 15
        assert obs.episode_done is False
        assert obs.task_description != ""

    def test_reset_produces_alarms(self):
        env = TelcoRCAEnvironment("easy")
        obs = env.reset()
        # Easy task with 20 nodes should produce some alarms
        assert obs.total_alarm_count >= 1

    def test_hard_reset(self):
        env = TelcoRCAEnvironment("hard")
        obs = env.reset()
        assert obs.steps_remaining == 50


class TestEnvironmentStep:
    def test_check_logs_action(self):
        env = TelcoRCAEnvironment("easy")
        obs = env.reset()
        alarm = obs.active_alarms[0] if obs.active_alarms else None
        if alarm:
            action = AgentAction(action_type="CHECK_LOGS", target_node_id=alarm.node_id)
            result = env.step(action)
            assert result.reward > -1.0
            assert result.done is False or result.done is True

    def test_invalid_node_penalty(self):
        env = TelcoRCAEnvironment("easy")
        env.reset()
        action = AgentAction(action_type="CHECK_LOGS", target_node_id="NONEXISTENT_999")
        result = env.step(action)
        assert result.reward < 0

    def test_episode_terminates_on_correct_restart(self):
        env = TelcoRCAEnvironment("easy")
        env.reset()
        root = env._state.root_cause_id
        action = AgentAction(action_type="RESTART", target_node_id=root)
        result = env.step(action)
        assert result.done is True
        assert result.reward > 0.5

    def test_false_positive_on_wrong_restart(self):
        env = TelcoRCAEnvironment("easy")
        obs = env.reset()
        root = env._state.root_cause_id
        wrong = next(
            nid for nid in env._state.nodes if nid != root
        )
        action = AgentAction(action_type="RESTART", target_node_id=wrong)
        result = env.step(action)
        assert result.reward < 0
        assert result.observation.false_positives_so_far == 1


class TestGraders:
    def test_score_range(self):
        for grade_fn in [grade_easy, grade_medium, grade_hard]:
            score = grade_fn({
                "root_cause_fixed": True,
                "steps_taken": 5,
                "false_positives": 0,
                "elapsed_seconds": 10,
            })
            assert 0.0 <= score <= 1.0, f"Score out of range: {score}"

    def test_zero_score_on_failure(self):
        score = grade_easy({
            "root_cause_fixed": False,
            "correct_diagnosis": False,
            "steps_taken": 15,
            "false_positives": 3,
            "elapsed_seconds": 300,
        })
        assert score == 0.0

    def test_better_score_fewer_steps(self):
        fast = grade_medium({
            "root_cause_fixed": True,
            "steps_taken": 3,
            "false_positives": 0,
            "elapsed_seconds": 5,
        })
        slow = grade_medium({
            "root_cause_fixed": True,
            "steps_taken": 28,
            "false_positives": 0,
            "elapsed_seconds": 280,
        })
        assert fast > slow

    def test_fp_penalty_reduces_score(self):
        clean = grade_hard({
            "root_cause_fixed": True,
            "steps_taken": 10,
            "false_positives": 0,
            "elapsed_seconds": 30,
        })
        dirty = grade_hard({
            "root_cause_fixed": True,
            "steps_taken": 10,
            "false_positives": 3,
            "elapsed_seconds": 30,
        })
        assert clean > dirty

    def test_grade_episode_breakdown(self):
        result = grade_episode(
            task_name="easy",
            root_cause_fixed=True,
            steps_taken=5,
            false_positives=0,
            elapsed_seconds=15,
        )
        assert "score" in result
        assert "breakdown" in result
        assert result["score"] > 0

    def test_deterministic(self):
        kwargs = dict(
            task_name="medium",
            root_cause_fixed=True,
            steps_taken=10,
            false_positives=1,
            elapsed_seconds=45,
        )
        assert grade_episode(**kwargs)["score"] == grade_episode(**kwargs)["score"]


class TestStateEndpoint:
    def test_state_before_reset(self):
        env = TelcoRCAEnvironment("easy")
        state = env.get_state()
        assert state["status"] == "not_started"

    def test_state_after_reset(self):
        env = TelcoRCAEnvironment("easy")
        env.reset()
        state = env.get_state()
        assert "root_cause_id" in state
        assert state["steps_taken"] == 0
