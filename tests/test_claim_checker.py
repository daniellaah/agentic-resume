from app.claim_checker import check_rewrite_claims


def test_claim_checker_accepts_rewrite_using_supported_source_facts():
    issues = check_rewrite_claims(
        source_text="Built internal REST APIs using Python and FastAPI.",
        rewritten_text="Built Python and FastAPI REST APIs for internal workflows.",
    )

    assert issues == []


def test_claim_checker_rejects_new_technology_claim():
    issues = check_rewrite_claims(
        source_text="Built internal REST APIs using Python and FastAPI.",
        rewritten_text=(
            "Built Python and FastAPI REST APIs and deployed them to Kubernetes."
        ),
    )

    assert len(issues) == 1
    assert issues[0].issue_type == "unsupported_claim"
    assert issues[0].severity == "critical"
    assert "Kubernetes" in issues[0].message


def test_claim_checker_rejects_new_numeric_claim():
    issues = check_rewrite_claims(
        source_text="Improved service validation for internal users.",
        rewritten_text="Improved service validation for 1m users.",
    )

    assert len(issues) == 1
    assert "1m" in issues[0].message


def test_claim_checker_rejects_new_scale_or_impact_claim():
    issues = check_rewrite_claims(
        source_text="Built internal REST APIs using Python and FastAPI.",
        rewritten_text="Built production Python and FastAPI APIs for enterprise users.",
    )

    assert len(issues) == 1
    assert "enterprise" in issues[0].message
    assert "production" in issues[0].message
    assert "users" in issues[0].message


def test_claim_checker_allows_technology_claim_already_in_source():
    issues = check_rewrite_claims(
        source_text="Containerized Python services with Docker.",
        rewritten_text="Built Docker-based Python service workflows.",
    )

    assert issues == []


def test_claim_checker_rejects_new_ab_testing_ownership_claim():
    issues = check_rewrite_claims(
        source_text=(
            "Developed offline evaluation with Recall@K before online A/B testing."
        ),
        rewritten_text=(
            "Developed and implemented A/B testing for collaborative filtering."
        ),
    )

    assert len(issues) == 1
    assert "A/B testing ownership" in issues[0].message


def test_claim_checker_allows_ab_testing_action_already_in_source():
    issues = check_rewrite_claims(
        source_text="Implemented A/B testing for ranking model experiments.",
        rewritten_text="Implemented A/B testing for recommendation experiments.",
    )

    assert issues == []
