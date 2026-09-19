from aihr.intelligence import resume


def test_strong_candidate_score_high():
    result = resume.screen_resume_rule_based(
        "5 years experience with python pandas sql and excel for business reporting",
        "Data Analyst",
        ["python", "pandas", "sql", "excel"],
        min_experience=2,
    )
    assert result["verdict"] == "Strong"
    assert result["score"] >= 80


def test_weak_candidate_score_low():
    result = resume.screen_resume_rule_based(
        "6 months internship using python",
        "ML Engineer",
        ["python", "pytorch", "aws"],
        min_experience=2,
    )
    assert result["verdict"] == "Weak"


def test_matches_skills_with_hyphen():
    result = resume.screen_resume_rule_based(
        "5 years python scikit learn and pandas",
        "ML Engineer",
        ["scikit-learn", "pandas"],
        min_experience=1,
    )
    assert "scikit-learn" in result["matched_skills"]


def test_missing_skills_reported():
    result = resume.screen_resume_rule_based(
        "python only",
        "Backend Engineer",
        ["python", "fastapi", "postgresql"],
        min_experience=1,
    )
    assert "fastapi" in result["missing_skills"]
    assert "postgresql" in result["missing_skills"]


def test_experience_extraction():
    result = resume.screen_resume_rule_based(
        "3 years 6 months of python experience",
        "Engineer",
        ["python"],
        min_experience=2,
    )
    assert result["experience_years"] == 3.0