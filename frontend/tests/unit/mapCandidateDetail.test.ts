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
    expect(presentation).not.toHaveProperty('suggestedTeam')
    expect(presentation).not.toHaveProperty('recommendedOwner')
    expect(presentation).not.toHaveProperty('technicalDebtOwner')
    expect(presentation).not.toHaveProperty('impactScore')
    expect(presentation).not.toHaveProperty('blastRadius')
    expect(serialized).not.toContain('CND-')
    expect(serialized).not.toContain('reviewStatus')
    expect(serialized).not.toContain('suggestedTeam')
    expect(serialized).not.toContain('recommendedOwner')
    expect(serialized).not.toContain('technicalDebtOwner')
  })
})

describe('toCandidateDetailPresentation enterprise and dependency context', () => {
  it('preserves enterprise asset name, key, and type', () => {
    const presentation = toCandidateDetailPresentation(detail)
    const asset = detail.enterprise_context.enterprise_asset

    expect(presentation.enterpriseContext.asset).toEqual({
      name: asset.name,
      assetKey: asset.asset_key,
      assetType: asset.asset_type,
      criticality: asset.criticality,
      lifecycleStatus: asset.lifecycle_status,
    })
    expect(presentation.enterpriseContext.asset.name).toBe('Orbit Catalog')
    expect(presentation.enterpriseContext.asset.assetKey).toBe('svc-orbit-catalog')
    expect(presentation.enterpriseContext.asset.assetType).toBe('SERVICE')
  })

  it('maps asset criticality as criticality, not risk', () => {
    const presentation = toCandidateDetailPresentation(detail)

    expect(presentation.enterpriseContext.asset.criticality).toBe('HIGH')
    expect(presentation.enterpriseContext.asset).not.toHaveProperty('risk')
    expect(presentation.candidate).not.toHaveProperty('risk')
    expect(presentation.enterpriseContext).not.toHaveProperty('risk')
  })

  it('preserves asset lifecycle status as lifecycle, not a decision state', () => {
    const presentation = toCandidateDetailPresentation(detail)

    expect(presentation.enterpriseContext.asset.lifecycleStatus).toBe('ACTIVE')
    expect(presentation.enterpriseContext.asset).not.toHaveProperty('validationStatus')
    expect(presentation.enterpriseContext.asset).not.toHaveProperty('decisionStatus')
  })

  it('maps enterprise ownership team name, team key, and ownership role', () => {
    const presentation = toCandidateDetailPresentation(detail)

    expect(presentation.enterpriseContext.ownerships).toEqual([
      {
        teamName: 'Orbit Platform Team',
        teamKey: 'team-orbit',
        ownershipRole: 'PRIMARY',
      },
    ])
  })

  it('does not present ownership as Candidate or TechnicalDebt ownership', () => {
    const presentation = toCandidateDetailPresentation(detail)
    const ownership = presentation.enterpriseContext.ownerships[0]

    expect(presentation).not.toHaveProperty('suggestedTeam')
    expect(presentation).not.toHaveProperty('recommendedOwner')
    expect(presentation).not.toHaveProperty('technicalDebtOwner')
    expect(presentation.enterpriseContext).not.toHaveProperty('suggestedTeam')
    expect(presentation.enterpriseContext).not.toHaveProperty('recommendedOwner')
    expect(presentation.enterpriseContext).not.toHaveProperty('technicalDebtOwner')
    expect(ownership).not.toHaveProperty('suggestedTeam')
    expect(ownership).not.toHaveProperty('recommendedOwner')
    expect(ownership).not.toHaveProperty('technicalDebtOwner')
  })

  it('preserves direct relationship source, target, and type without causality', () => {
    const presentation = toCandidateDetailPresentation(detail)
    const relationship = presentation.enterpriseContext.relationships[0]

    expect(relationship).toEqual({
      sourceAssetKey: 'app-orbit',
      targetAssetKey: 'svc-orbit-catalog',
      relationshipType: 'IMPLEMENTED_BY',
    })
    expect(relationship).not.toHaveProperty('causality')
    expect(relationship).not.toHaveProperty('willFail')
    expect(relationship).not.toHaveProperty('impact')
  })

  it('preserves incident key, title, severity, started_at, and resolved_at', () => {
    const presentation = toCandidateDetailPresentation(detail)
    const incident = presentation.enterpriseContext.incidents[0]

    expect(incident).toEqual({
      incidentKey: 'inc-orbit-001',
      title: 'Catalog timeouts',
      severity: 'HIGH',
      startedAt: '2026-08-01T08:00:00+00:00',
      resolvedAt: null,
      primaryAffectedAssetKey: 'svc-orbit-catalog',
    })
  })

  it('keeps a null incident resolved_at as null', () => {
    const presentation = toCandidateDetailPresentation(detail)

    expect(presentation.enterpriseContext.incidents[0]?.resolvedAt).toBeNull()
  })

  it('does not map incident severity to Candidate risk', () => {
    const presentation = toCandidateDetailPresentation(detail)
    const incident = presentation.enterpriseContext.incidents[0]

    expect(incident?.severity).toBe('HIGH')
    expect(incident).not.toHaveProperty('risk')
    expect(presentation.candidate).not.toHaveProperty('risk')
    expect(presentation).not.toHaveProperty('risk')
  })

  it('maps a recorded incident resolved_at value without inventing status text', () => {
    const resolvedDetail: CandidateDetailResponse = {
      ...detail,
      enterprise_context: {
        ...detail.enterprise_context,
        direct_incidents: [
          {
            ...detail.enterprise_context.direct_incidents[0]!,
            resolved_at: '2026-08-02T09:00:00+00:00',
          },
        ],
      },
    }

    const presentation = toCandidateDetailPresentation(resolvedDetail)

    expect(presentation.enterpriseContext.incidents[0]?.resolvedAt).toBe(
      '2026-08-02T09:00:00+00:00',
    )
    expect(presentation.enterpriseContext.incidents[0]).not.toHaveProperty('activeOutage')
    expect(presentation.enterpriseContext.incidents[0]).not.toHaveProperty('status')
  })

  it('maps dependency anchors, dependencies, dependents, and reachable dependents exactly', () => {
    const presentation = toCandidateDetailPresentation(detail)

    expect(presentation.dependencyContext.dependencyAnchors).toEqual([
      { assetKey: 'svc-orbit-catalog', assetType: 'SERVICE' },
    ])
    expect(presentation.dependencyContext.directDependencies).toEqual([])
    expect(presentation.dependencyContext.directDependents).toEqual([
      { assetKey: 'svc-asteria-editor', assetType: 'SERVICE' },
    ])
    expect(presentation.dependencyContext.reachableDependents).toEqual([
      { assetKey: 'svc-asteria-editor', assetType: 'SERVICE' },
    ])
    expect(presentation.dependencyContext.candidateAsset).toEqual({
      assetKey: 'svc-orbit-catalog',
      assetType: 'SERVICE',
    })
  })

  it('does not infer reachable dependents or impact from other collections', () => {
    const graphDetail: CandidateDetailResponse = {
      ...detail,
      dependency_context: {
        ...detail.dependency_context,
        dependency_anchors: [{ asset_key: 'svc-orbit-catalog', asset_type: 'SERVICE' }],
        direct_dependencies: [{ asset_key: 'svc-ledger', asset_type: 'SERVICE' }],
        direct_dependents: [{ asset_key: 'svc-asteria-editor', asset_type: 'SERVICE' }],
        reachable_dependents: [
          { asset_key: 'svc-asteria-editor', asset_type: 'SERVICE' },
          { asset_key: 'svc-borealis-renderer', asset_type: 'SERVICE' },
        ],
      },
    }

    const presentation = toCandidateDetailPresentation(graphDetail)

    expect(presentation.dependencyContext.directDependencies).toEqual([
      { assetKey: 'svc-ledger', assetType: 'SERVICE' },
    ])
    expect(presentation.dependencyContext.directDependents).toEqual([
      { assetKey: 'svc-asteria-editor', assetType: 'SERVICE' },
    ])
    expect(presentation.dependencyContext.reachableDependents).toEqual([
      { assetKey: 'svc-asteria-editor', assetType: 'SERVICE' },
      { assetKey: 'svc-borealis-renderer', assetType: 'SERVICE' },
    ])
    expect(presentation.dependencyContext).not.toHaveProperty('impactedSystems')
    expect(presentation.dependencyContext).not.toHaveProperty('blastRadius')
    expect(presentation.dependencyContext).not.toHaveProperty('impactScore')
    expect(presentation.dependencyContext).not.toHaveProperty('expectedOutage')
  })

  it('maps empty enterprise and dependency collections as empty arrays', () => {
    const emptyDetail: CandidateDetailResponse = {
      ...detail,
      enterprise_context: {
        ...detail.enterprise_context,
        enterprise_ownerships: [],
        direct_relationships: [],
        direct_incidents: [],
      },
      dependency_context: {
        ...detail.dependency_context,
        dependency_anchors: [],
        direct_dependencies: [],
        direct_dependents: [],
        reachable_dependents: [],
      },
    }

    const presentation = toCandidateDetailPresentation(emptyDetail)

    expect(presentation.enterpriseContext.ownerships).toEqual([])
    expect(presentation.enterpriseContext.relationships).toEqual([])
    expect(presentation.enterpriseContext.incidents).toEqual([])
    expect(presentation.dependencyContext.dependencyAnchors).toEqual([])
    expect(presentation.dependencyContext.directDependencies).toEqual([])
    expect(presentation.dependencyContext.directDependents).toEqual([])
    expect(presentation.dependencyContext.reachableDependents).toEqual([])
  })
})
