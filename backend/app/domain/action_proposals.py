import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

_CANONICAL_FINGERPRINT_FIELDS = (
    "action_type",
    "body",
    "target_repository_name",
    "target_repository_owner",
    "title",
)


class ActionType(StrEnum):
    CREATE_GITHUB_ISSUE = "CREATE_GITHUB_ISSUE"


@dataclass(frozen=True)
class GitHubIssuePayload:
    """Exact GitHub issue title and body a human may later approve."""

    title: str
    body: str

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("GitHub issue title must not be blank")
        if not self.body.strip():
            raise ValueError("GitHub issue body must not be blank")


def action_proposal_reconciliation_marker(action_proposal_id: UUID) -> str:
    """Return the deterministic marker derived from the proposal identity.

    Later packages may search GitHub for this marker after a lost local
    response. Package 2 only persists it; it never calls GitHub.
    """
    return f"tdiq-action-proposal:{action_proposal_id}"


def canonical_action_payload_fingerprint(
    *,
    action_type: str,
    target_repository_owner: str,
    target_repository_name: str,
    title: str,
    body: str,
) -> str:
    """Return the SHA-256 hex digest of the exact approved mutation semantics.

    Canonical input is only:

    - action_type
    - target_repository_owner
    - target_repository_name
    - exact final title
    - exact final body

    The body must already be complete, including the reconciliation marker
    when that marker is embedded in the proposed GitHub issue body.

    Timestamps, actor, database row order, and other non-semantic runtime
    metadata are excluded. The same canonical input always yields the same
    fingerprint.
    """
    canonical = json.dumps(
        {
            "action_type": action_type,
            "body": body,
            "target_repository_name": target_repository_name,
            "target_repository_owner": target_repository_owner,
            "title": title,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    if tuple(json.loads(canonical)) != _CANONICAL_FINGERPRINT_FIELDS:
        raise RuntimeError("Canonical fingerprint field set is not stable")
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ActionProposal:
    """Immutable preview of one exact external mutation. Not an approval."""

    action_proposal_id: UUID
    technical_debt_id: UUID
    action_type: ActionType
    target_repository_owner: str
    target_repository_name: str
    payload: GitHubIssuePayload
    payload_fingerprint: str
    reconciliation_marker: str
    prepared_by: str
    created_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.action_type, ActionType):
            raise ValueError("ActionProposal action type must be supported")
        if self.action_type is not ActionType.CREATE_GITHUB_ISSUE:
            raise ValueError("ActionProposal action type must be CREATE_GITHUB_ISSUE")
        if not isinstance(self.payload, GitHubIssuePayload):
            raise ValueError("ActionProposal payload must be a GitHub issue payload")
        if not self.target_repository_owner.strip():
            raise ValueError("ActionProposal target repository owner must not be blank")
        if not self.target_repository_name.strip():
            raise ValueError("ActionProposal target repository name must not be blank")
        if not self.prepared_by.strip():
            raise ValueError("ActionProposal prepared_by must not be blank")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("ActionProposal created timestamp must be timezone-aware")

        expected_marker = action_proposal_reconciliation_marker(self.action_proposal_id)
        if self.reconciliation_marker != expected_marker:
            raise ValueError(
                "ActionProposal reconciliation marker must match the proposal identity"
            )
        if expected_marker not in self.payload.body:
            raise ValueError(
                "ActionProposal body must include the reconciliation marker"
            )

        expected_fingerprint = canonical_action_payload_fingerprint(
            action_type=self.action_type.value,
            target_repository_owner=self.target_repository_owner,
            target_repository_name=self.target_repository_name,
            title=self.payload.title,
            body=self.payload.body,
        )
        if self.payload_fingerprint != expected_fingerprint:
            raise ValueError(
                "ActionProposal payload fingerprint does not match canonical input"
            )
