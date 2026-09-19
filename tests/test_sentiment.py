from aihr.intelligence import sentiment


def test_positive_feedback_scores_positive():
    result = sentiment.score_feedback_rule_based("good", "Team is helpful and I feel great")
    assert result["sentiment_score"] > 0
    assert result["urgency_level"] == "low"


def test_negative_feedback_flags_high_urgency():
    result = sentiment.score_feedback_rule_based(
        "stressed", "Too many deadlines and I feel exhausted and overwhelmed"
    )
    assert result["sentiment_score"] < 0
    assert result["urgency_level"] == "high"
    assert result["needs_follow_up"] is True


def test_mood_scores_are_bounded():
    for mood in ("great", "good", "okay", "stressed", "struggling"):
        result = sentiment.score_feedback_rule_based(mood, "")
        assert -1.0 <= result["sentiment_score"] <= 1.0


def test_theme_extraction():
    result = sentiment.score_feedback_rule_based("okay", "workload too much pressure deadlines")
    assert "workload" in result["key_themes"]


def test_defaults_low():
    result = sentiment.score_feedback_rule_based("", "")
    assert result["sentiment_score"] == 0.0
    assert result["urgency_level"] == "low"
    assert result["attrition_risk"] == "low"