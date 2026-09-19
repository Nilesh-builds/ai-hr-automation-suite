from aihr.intelligence import leave


def test_parses_iso_range():
    result = leave.parse_leave_rule_based(
        "I need 3 days off from 2026-08-12 to 2026-08-14 for personal reasons"
    )
    assert result["parsed"] is True
    assert result["start_date"] == "2026-08-12"
    assert result["end_date"] == "2026-08-14"
    assert result["duration_days"] == 3
    assert result["leave_type"] == "personal"


def test_detects_sick_leave():
    result = leave.parse_leave_rule_based("Going on sick leave tomorrow")
    assert result["leave_type"] == "sick"
    assert result["parsed"] is True


def test_handles_dm_y_format():
    result = leave.parse_leave_rule_based("Need a casual leave day on 12/08/2026")
    assert result["start_date"] == "2026-08-12"
    assert result["leave_type"] == "casual"


def test_unpaid_not_mistaken_for_sick():
    result = leave.parse_leave_rule_based("Take unpaid leave from 2026-12-20 till 2026-12-24")
    assert result["leave_type"] == "unpaid"


def test_returns_unparsed_when_no_date():
    result = leave.parse_leave_rule_based("I want some time off soon, maybe")
    assert result["parsed"] is False
    assert result["confidence"] == 0.0


def test_multi_date_duration():
    result = leave.parse_leave_rule_based("Annual leave 2026-10-01 to 2026-10-03")
    assert result["duration_days"] == 3
    assert result["start_date"] == "2026-10-01"