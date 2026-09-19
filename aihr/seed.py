"""Seed the SQLite store with realistic synthetic HR data for demos.

Run standalone: python -m aihr.seed
"""

from __future__ import annotations

import random
from datetime import date, timedelta

from .intelligence import leave, resume, sentiment
from .models import Employee, NewHire, Policy
from .store import HRStore

random.seed(42)

EMPLOYEES = [
    Employee("E1001", "Aarav", "Sharma", "aarav.sharma@example.com", "Active", "Engineering"),
    Employee("E1002", "Diya", "Patel", "diya.patel@example.com", "Active", "Sales"),
    Employee("E1003", "Kabir", "Nair", "kabir.nair@example.com", "Active", "Support"),
    Employee("E1004", "Ishita", "Reddy", "ishita.reddy@example.com", "Active", "Engineering"),
    Employee("E1005", "Vihaan", "Singh", "vihaan.singh@example.com", "Active", "Marketing"),
    Employee("E1006", "Ananya", "Kulkarni", "ananya.kulkarni@example.com", "Active", "Finance"),
    Employee("E1007", "Rohan", "Mehta", "rohan.mehta@example.com", "Active", "Support"),
    Employee("E1008", "Sara", "Khan", "sara.khan@example.com", "Active", "Engineering"),
    Employee("E1009", "Aditya", "Joshi", "aditya.joshi@example.com", "Active", "Sales"),
    Employee("E1010", "Nisha", "Devi", "nisha.devi@example.com", "Active", "HR"),
]

HIRES = [
    NewHire("H-101", "Arjun", "Das", "arjun.das@example.com", date.today() + timedelta(days=2), "Engineering"),
    NewHire("H-102", "Meera", "Nair", "meera.nair@example.com", date.today() + timedelta(days=8), "Design"),
    NewHire("H-103", "Farhan", "Ali", "farhan.ali@example.com", date.today() + timedelta(days=20), "Sales"),
    NewHire("H-104", "Grisha", "Kohli", "grisha.kohli@example.com", date.today() + timedelta(days=45), "Finance"),
]

LEAVE_SAMPLES = [
    ("E1001", "I need 3 days off from 2026-08-12 to 2026-08-14 for personal reasons", "approved"),
    ("E1003", "Going on sick leave tomorrow", "approved"),
    ("E1005", "Book annual leave 2026-10-01 to 2026-10-03 for my family trip", "pending"),
    ("E1002", "Need a casual leave day on 2026-09-20 for a family function", "approved"),
    ("E1007", "2 days annual leave for 2026-11-11 and 2026-11-12", "pending"),
    ("E1008", "Moving to a new house, personal leave 2026-06-01 to 2026-06-02", "approved"),
]

FEEDBACK_ROWS = [
    ("E1001", "great", "I love the new project and my manager is very supportive"),
    ("E1002", "good", "Team is helpful and we shipped on time"),
    ("E1003", "okay", "Workload is a bit too much lately, deadlines everywhere"),
    ("E1004", "stressed", "Too many deadlines this quarter and I feel exhausted"),
    ("E1005", "struggling", "Underpaid and with no growth path, thinking about options"),
    ("E1006", "good", "Grateful for the extra benefits this quarter"),
    ("E1007", "okay", "Training sessions helped me a lot, happy with that"),
    ("E1008", "stressed", "My manager is unfair and micromanages everything"),
    ("E1009", "good", "Excellent work-life balance now"),
    ("E1010", "great", "Really enjoy the team culture and leadership support"),
]

POLICIES = {
    "POL-LEAVE-01": Policy("POL-LEAVE-01", "Annual Leave Policy", "Employees are entitled to 20 days of annual leave per year. Leave must be requested at least 3 days in advance and approved by the manager.", "Leave"),
    "POL-LEAVE-02": Policy("POL-LEAVE-02", "Sick Leave Policy", "Employees may take up to 8 days of sick leave per year without documentation. More than 3 consecutive days requires a medical certificate.", "Leave"),
    "POL-LEAVE-03": Policy("POL-LEAVE-03", "Casual Leave Policy", "Each employee receives 6 days of casual leave per year for non-planned time off. Casual leave cannot be taken in the first year of probation.", "Leave"),
    "POL-WORK-01": Policy("POL-WORK-01", "Remote Work Policy", "Staff may work from home up to 2 days per week with manager approval. All remote days must be logged in the attendance system.", "Work"),
    "POL-EXP-01": Policy("POL-EXP-01", "Expense Reimbursement Policy", "Travel and training expenses are reimbursed within 15 working days when a receipt and approval form are submitted within 30 days of the expense.", "Finance"),
    "POL-FLT-01": Policy("POL-FLT-01", "Employee Benefits Policy", "Employees qualify for health insurance after 3 months of employment. Annual performance reviews determine bonus and raise eligibility.", "Benefits"),
    "POL-NOT-01": Policy("POL-NOT-01", "Resignation Notice Policy", "Employees must give 30 days written notice when resigning. Notice period may be reduced at management's discretion.", "Leave"),
}

CANDIDATES = [
    ("CA-01", "Asha Rao", "Data Analyst", "5 years experience with python pandas sql and excel for business reporting", ["python", "pandas", "sql", "excel"]),
    ("CA-02", "Priya Iyer", "Data Analyst", "8 years of reporting with python pandas sql and tableau and powerbi", ["python", "pandas", "sql", "tableau"]),
    ("CA-03", "Dinesh Patel", "ML Engineer", "4 years experience with python pytorch and deploying models to aws", ["python", "pytorch", "aws"]),
    ("CA-04", "Arjun Das", "Backend Engineer", "6 months internship using python and basic api development", ["python", "fastapi", "postgresql"]),
]

POLICY_QUESTIONS = [
    ("E1001", "How many annual leave days do I get each year?"),
    ("E1003", "Do I need a medical certificate for 4 days of sick leave?"),
    ("E1005", "Can I take casual leave during my probation period?"),
    ("E1008", "What is the reimbursement rule for travel?"),
    ("E1010", "How much notice do I need when resigning?"),
]


def seed():
    store = HRStore()

    for emp in EMPLOYEES:
        store.upsert_employee(emp)
    for hire in HIRES:
        store.upsert_new_hire(hire)
    for policy in POLICIES.values():
        store.upsert_policy(policy)

    for employee_id, text, reason in LEAVE_SAMPLES:
        parsed = leave.parse_leave_rule_based(text)
        store.insert_leave_request({
            "employee_id": employee_id, "text": text, "reason": reason,
            **{k: parsed[k] for k in ("start_date", "end_date", "duration_days", "leave_type", "confidence")},
            "approved": reason == "approved",
        })

    for employee_id, mood, comments in FEEDBACK_ROWS:
        analysis = sentiment.score_feedback_rule_based(mood, comments)
        days_ago = random.randint(0, 30)
        store.insert_feedback({
            "employee_id": employee_id, "mood": mood, "comments": comments,
            "submitted_at": (date.today() - timedelta(days=days_ago)).isoformat(),
            **analysis,
        })

    for candidate_id, name, role, text, skills in CANDIDATES:
        result = resume.screen_resume_rule_based(text, role, skills, min_experience=2)
        store.insert_candidate({
            "candidate_id": candidate_id, "name": name, "resume_text": text, "role": role,
            **result,
        })

    from .intelligence import policy as policy_mod

    for employee_id, question in POLICY_QUESTIONS:
        answer = policy_mod.answer_policy_rule_based(question, list(POLICIES.values()))
        store.insert_policy_query({
            "employee_id": employee_id, "question": question,
            "created_at": (date.today() - timedelta(days=random.randint(0, 20))).isoformat(),
            **answer,
        })

    return store


if __name__ == "__main__":
    store = seed()
    print("seeded:", store.summary())