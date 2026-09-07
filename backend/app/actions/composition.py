from uuid import UUID

from app.domain.action_proposals import action_proposal_reconciliation_marker
from app.domain.candidates import Candidate
from app.domain.technical_debts import TechnicalDebt


def compose_github_issue_title(candidate: Candidate) -> str:
    """Compose a compact remediation-issue title from persisted Candidate truth."""
    return f"Technical debt: {candidate.canonical_asset.asset_key}"


def compose_github_issue_body(
    *,
    technical_debt: TechnicalDebt,
    candidate: Candidate,
    action_proposal_id: UUID,
) -> str:
    """Compose the exact GitHub issue body, including the reconciliation marker.

    The marker is embedded in the final body before fingerprinting. Composition
    uses only persisted TechnicalDebt and Candidate facts.
    """
    marker = action_proposal_reconciliation_marker(action_proposal_id)
    asset = candidate.canonical_asset
    return (
        "Technical debt remediation tracking issue\n"
        "\n"
        f"technical_debt_id: {technical_debt.technical_debt_id}\n"
        f"source_candidate_id: {candidate.candidate_id}\n"
        f"canonical_asset: {asset.asset_key} ({asset.asset_type.value})\n"
        f"hypothesis: {candidate.hypothesis}\n"
        "\n"
        f"{marker}\n"
    )
