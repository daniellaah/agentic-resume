import re

from app.models import ValidationIssue

TERM_PATTERN = re.compile(r"[a-z0-9+#.]+(?:[-/][a-z0-9+#.]+)*", re.IGNORECASE)
NUMERIC_CLAIM_PATTERN = re.compile(r"\b\d+(?:\.\d+)?(?:%|x|k|m|ms|s)?\b")

TECHNOLOGY_ALIASES = {
    "aws": "AWS",
    "azure": "Azure",
    "celery": "Celery",
    "django": "Django",
    "docker": "Docker",
    "fastapi": "FastAPI",
    "flask": "Flask",
    "gcp": "GCP",
    "graphql": "GraphQL",
    "javascript": "JavaScript",
    "k8s": "Kubernetes",
    "kafka": "Kafka",
    "kubernetes": "Kubernetes",
    "next.js": "Next.js",
    "node": "Node.js",
    "node.js": "Node.js",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "python": "Python",
    "pytest": "pytest",
    "react": "React",
    "redis": "Redis",
    "typescript": "TypeScript",
}

SCALE_AND_IMPACT_TERMS = {
    "customers",
    "enterprise",
    "high-scale",
    "improved",
    "increased",
    "large-scale",
    "latency",
    "millions",
    "optimized",
    "performance",
    "production",
    "reduced",
    "revenue",
    "throughput",
    "users",
}


def check_rewrite_claims(
    source_text: str,
    rewritten_text: str,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    source_technologies = _extract_technologies(source_text)
    rewritten_technologies = _extract_technologies(rewritten_text)
    new_technologies = sorted(rewritten_technologies - source_technologies)
    if new_technologies:
        issues.append(
            _unsupported_claim_issue(
                "Unsupported technology claims introduced: "
                f"{', '.join(new_technologies)}."
            )
        )

    source_numbers = _extract_numeric_claims(source_text)
    rewritten_numbers = _extract_numeric_claims(rewritten_text)
    new_numbers = sorted(rewritten_numbers - source_numbers)
    if new_numbers:
        issues.append(
            _unsupported_claim_issue(
                "Unsupported numeric or metric claims introduced: "
                f"{', '.join(new_numbers)}."
            )
        )

    source_claim_terms = _extract_scale_and_impact_terms(source_text)
    rewritten_claim_terms = _extract_scale_and_impact_terms(rewritten_text)
    new_claim_terms = sorted(rewritten_claim_terms - source_claim_terms)
    if new_claim_terms:
        issues.append(
            _unsupported_claim_issue(
                "Unsupported scale or impact claims introduced: "
                f"{', '.join(new_claim_terms)}."
            )
        )

    return issues


def _extract_technologies(text: str) -> set[str]:
    return {
        canonical_term
        for term in _extract_terms(text)
        if (canonical_term := TECHNOLOGY_ALIASES.get(term)) is not None
    }


def _extract_numeric_claims(text: str) -> set[str]:
    return set(NUMERIC_CLAIM_PATTERN.findall(text.lower()))


def _extract_scale_and_impact_terms(text: str) -> set[str]:
    return _extract_terms(text) & SCALE_AND_IMPACT_TERMS


def _extract_terms(text: str) -> set[str]:
    terms: set[str] = set()
    for raw_term in TERM_PATTERN.findall(text.lower()):
        term = raw_term.strip(".,;:!?()[]{}\"'")
        if not term:
            continue

        terms.add(term)
        for separator in ("-", "/"):
            if separator in term:
                terms.update(part for part in term.split(separator) if part)

    return terms


def _unsupported_claim_issue(message: str) -> ValidationIssue:
    return ValidationIssue(
        issue_type="unsupported_claim",
        severity="critical",
        message=message,
    )
