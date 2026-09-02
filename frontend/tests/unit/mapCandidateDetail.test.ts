import { describe, expect, it } from 'vitest'
import type { CandidateDetailResponse } from '../../app/types/candidateApi'
import { toCandidateDetailPresentation } from '../../app/utils/mapCandidateDetail'

const CANDIDATE_ID = '20000000-0000-0000-0000-000000000001'
const SIGNAL_WITH_SEVERITY_ID = '00000000-0000-0000-0000-000000000011'
const SIGNAL_WITHOUT_SEVERITY_ID = '00000000-0000-0000-0000-000000000012'
const EVIDENCE_WITH_URI_ID = '10000000-0000-0000-0000-000000000011'
const EVIDENCE_WITHOUT_URI_ID = '10000000-0000-0000-0000-000000000012'

const detail: CandidateDetailResponse = {
  candidate: {
    candidate_id: CANDIDATE_ID,
    signal_ids: [SIGNAL_WITH_SEVERITY_ID, SIGNAL_WITHOUT_SEVERITY_ID],
    evidence_ids: [EVIDENCE_WITH_URI_ID, EVIDENCE_WITHOUT_URI_ID],
    canonical_asset: {
      asset_key: 'svc-orbit-catalog',
      asset_type: 'SERVICE',
    },
    hypothesis: 'Potential missing request timeout',
    correlation_rationale: 'Exact canonical asset and deterministic problem family.',
  },
  signals: [
    {
      signal_id: SIGNAL_WITH_SEVERITY_ID,
      source_system: 'candidate-api-test',
      source_record_id: 'member-earlier',
      detected_at: '2026-08-31T10:00:00+00:00',
      signal_type: 'MISSING_TIMEOUT',
      affected_asset: {
        asset_key: 'svc-orbit-catalog',
        asset_type: 'SERVICE',
      },
      severity: 'MEDIUM',
      evidence_ids: [EVIDENCE_WITH_URI_ID],
    },
    {
      signal_id: SIGNAL_WITHOUT_SEVERITY_ID,
      source_system: 'semgrep',
      source_record_id: 'finding-without-severity',
      detected_at: '2026-08-31T11:00:00+00:00',
      signal_type: 'SATD_COMMENT',
      affected_asset: {
        asset_key: 'svc-orbit-catalog',
        asset_type: 'SERVICE',
      },
      severity: null,
      evidence_ids: [EVIDENCE_WITHOUT_URI_ID],
    },
  ],
  evidence: [
    {
      evidence_id: EVIDENCE_WITH_URI_ID,
      source_system: 'candidate-api-test',
      source_reference: 'evidence:member-earlier',
      captured_at: '2026-08-31T10:01:00+00:00',
      reference_uri: 'https://synthetic.invalid/member-earlier',
    },
    {
      evidence_id: EVIDENCE_WITHOUT_URI_ID,
      source_system: 'semgrep',
      source_reference: 'finding:without-uri',
      captured_at: '2026-08-31T11:01:00+00:00',
      reference_uri: null,
    },
  ],
  enterprise_context: {
    candidate_id: CANDIDATE_ID,
    enterprise_asset: {
      asset_key: 'svc-orbit-catalog',
      asset_type: 'SERVICE',
      name: 'Orbit Catalog',
      criticality: 'HIGH',
      lifecycle_status: 'ACTIVE',
    },
    enterprise_ownerships: [
      {
        asset_ownership: {
          asset_key: 'svc-orbit-catalog',
          team_key: 'team-orbit',
          ownership_role: 'PRIMARY',
        },
        team: { team_key: 'team-orbit', name: 'Orbit Platform Team' },
      },
    ],
    direct_relationships: [
      {
        source_asset_key: 'app-orbit',
        target_asset_key: 'svc-orbit-catalog',
        relationship_type: 'IMPLEMENTED_BY',
      },
    ],
    direct_incidents: [
      {
        incident_key: 'inc-orbit-001',
        primary_affected_asset_key: 'svc-orbit-catalog',
        severity: 'HIGH',
        title: 'Catalog timeouts',
        started_at: '2026-08-01T08:00:00+00:00',
        resolved_at: null,
      },
    ],
  },
  dependency_context: {
    candidate_id: CANDIDATE_ID,
    candidate_asset: {
      asset_key: 'svc-orbit-catalog',
      asset_type: 'SERVICE',
    },
    dependency_anchors: [
      {
        asset_key: 'svc-orbit-catalog',
        asset_type: 'SERVICE',
      },
    ],
    direct_dependencies: [],
    direct_dependents: [
      {
        asset_key: 'svc-asteria-editor',
        asset_type: 'SERVICE',
      },
    ],
    reachable_dependents: [
      {
        asset_key: 'svc-asteria-editor',
        asset_type: 'SERVICE',
      },
    ],
  },
}

describe('toCandidateDetailPresentation', () => {
  it('preserves the real Candidate UUID without a CND alias', () => {
    const presentation = toCandidateDetailPresentation(detail)

    expect(presentation.candidate.candidateId).toBe(CANDIDATE_ID)
    expect(presentation.candidate.candidateId).not.toMatch(/^CND-/)
    expect(presentation.candidate).not.toHaveProperty('id')
  })

  it('maps only factual Candidate fields from the Detail API', () => {
    const presentation = toCandidateDetailPresentation(detail)

    expect(presentation.candidate).toEqual({
      candidateId: CANDIDATE_ID,
      hypothesis: 'Potential missing request timeout',
      canonicalAssetKey: 'svc-orbit-catalog',
      canonicalAssetType: 'SERVICE',
      assetDisplayName: 'Orbit Catalog',
      correlationRationale: 'Exact canonical asset and deterministic problem family.',
    })
  })

  it('presents correlation_rationale as correlation context, not validation', () => {
    const presentation = toCandidateDetailPresentation(detail)

    expect(presentation.candidate.correlationRationale).toBe(detail.candidate.correlation_rationale)
    expect(presentation.candidate).not.toHaveProperty('validationRationale')
    expect(presentation.candidate).not.toHaveProperty('validationStatus')
    expect(presentation).not.toHaveProperty('reviewStatus')
  })

  it('maps Signal membership from the Detail API collection', () => {
    const presentation = toCandidateDetailPresentation(detail)

    expect(presentation.signals).toEqual([
      {
        signalId: SIGNAL_WITH_SEVERITY_ID,
        signalType: 'MISSING_TIMEOUT',
        sourceSystem: 'candidate-api-test',
        sourceRecordId: 'member-earlier',
        affectedAssetKey: 'svc-orbit-catalog',
        affectedAssetType: 'SERVICE',
        detectedAt: '2026-08-31T10:00:00+00:00',
        severity: 'MEDIUM',
      },
      {
        signalId: SIGNAL_WITHOUT_SEVERITY_ID,
        signalType: 'SATD_COMMENT',
        sourceSystem: 'semgrep',
        sourceRecordId: 'finding-without-severity',
        affectedAssetKey: 'svc-orbit-catalog',
        affectedAssetType: 'SERVICE',
        detectedAt: '2026-08-31T11:00:00+00:00',
        severity: null,
      },
    ])
  })

  it('keeps nullable Signal severity as null instead of inventing a value', () => {
    const presentation = toCandidateDetailPresentation(detail)

    expect(presentation.signals[1]?.severity).toBeNull()
    expect(presentation.signals[1]).not.toHaveProperty('risk')
  })

  it('maps Evidence provenance from source_system, source_reference, and captured_at', () => {
    const presentation = toCandidateDetailPresentation(detail)

    expect(presentation.evidence[0]).toEqual({
      evidenceId: EVIDENCE_WITH_URI_ID,
      sourceSystem: 'candidate-api-test',
      sourceReference: 'evidence:member-earlier',
      capturedAt: '2026-08-31T10:01:00+00:00',
      referenceUri: 'https://synthetic.invalid/member-earlier',
    })
  })

  it('keeps a null Evidence reference_uri as null', () => {
    const presentation = toCandidateDetailPresentation(detail)

    expect(presentation.evidence[1]?.referenceUri).toBeNull()
    expect(presentation.evidence[1]).not.toHaveProperty('summary')
  })

  it('does not invent governance, scoring, or mock Detail fields', () => {
    const presentation = toCandidateDetailPresentation(detail)
    const serialized = JSON.stringify(presentation)

    expect(presentation.candidate).not.toHaveProperty('reviewStatus')
    expect(presentation.candidate).not.toHaveProperty('suggestedTeam')
    expect(presentation.candidate).not.toHaveProperty('risk')
    expect(presentation.candidate).not.toHaveProperty('effort')
    expect(presentation.candidate).not.toHaveProperty('priority')
    expect(presentation.candidate).not.toHaveProperty('confidence')
    expect(presentation).not.toHaveProperty('enterprise_ownerships')
    expect(presentation).not.toHaveProperty('direct_relationships')
    expect(presentation).not.toHaveProperty('direct_incidents')
    expect(presentation).not.toHaveProperty('dependency_context')
    expect(serialized).not.toContain('CND-')
    expect(serialized).not.toContain('reviewStatus')
    expect(serialized).not.toContain('suggestedTeam')
  })
})
