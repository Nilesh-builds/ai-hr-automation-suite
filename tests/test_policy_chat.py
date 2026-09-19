from datetime import date, timedelta

from aihr.intelligence import policy, whatsapp
from aihr.models import Policy

POLICIES = [
    Policy("POL-LEAVE-01", "Annual Leave Policy",
           "Employees are entitled to 20 days of annual leave per year.", "Leave"),
    Policy("POL-WORK-01", "Remote Work Policy",
           "Staff may work from home up to 2 days per week with manager approval.", "Work"),
    Policy("POL-NOT-01", "Resignation Notice Policy",
           "Employees must give 30 days written notice when resigning.", "Leave"),
]


def test_retrieves_correct_policy():
    result = policy.answer_policy_rule_based(
        "How many annual leave days do I get each year?", POLICIES
    )
    assert result["policy_ids"] == ["POL-LEAVE-01"]
    assert result["grounded"] is True


def test_grounded_false_on_unrelated_question():
    result = policy.answer_policy_rule_based("Is the office pet friendly?", POLICIES)
    assert result["grounded"] is False
    assert result["policy_ids"] == []


def test_stemmed_plural_match():
    result = policy.answer_policy_rule_based("Are bonuses mentioned in policies?", POLICIES)
    assert result["grounded"] is False


def test_whatsapp_greeting():
    msg = whatsapp.route_intent_rule_based("Hello")
    assert msg.intent == "greeting"
    assert msg.confidence > 0.9


def test_whatsapp_leave_balance():
    msg = whatsapp.route_intent_rule_based("What is my leave balance?")
    assert msg.intent == "leave_balance"


def test_whatsapp_unknown():
    msg = whatsapp.route_intent_rule_based("What is the CEO's favorite color?")
    assert msg.intent == "unknown"