from datetime import date, timedelta

from aihr.intelligence import onboarding


def test_tasks_due_far_in_future():
    tasks = onboarding.tasks_due(date.today() + timedelta(days=60))
    assert tasks == []


def test_welcome_email_scheduled_within_lead_time():
    tasks = onboarding.tasks_due(date.today() + timedelta(days=10), today=date.today())
    names = {t.task_id for t in tasks}
    assert "welcome-email" in names
    assert "it-setup" not in names


def test_day1_only_within_one_day():
    tasks = onboarding.tasks_due(date.today() + timedelta(days=1), today=date.today())
    task_ids = {t.task_id for t in tasks}
    assert "day1-checklist" in task_ids


def test_onboarding_progress_all_pending():
    start = date.today() + timedelta(days=2)
    progress = onboarding.onboarding_progress(start, set(), today=date.today())
    assert progress["completed"] == 0
    assert progress["pending"] == progress["total"]
    assert progress["progress"] == 0.0


def test_onboarding_progress_partial():
    start = date.today() + timedelta(days=1)
    progress = onboarding.onboarding_progress(start, {"welcome-email", "it-setup"}, today=date.today())
    assert progress["completed"] >= 2
    assert progress["progress"] > 0.0