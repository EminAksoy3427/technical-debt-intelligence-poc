import type { CandidateDetailView } from '../types/candidate'

/**
 * Controlled, fictional presentation data for Candidate Detail.
 * This is not a backend API response or canonical domain contract.
 */
export const mockCandidateDetails: CandidateDetailView[] = [
  {
    id: 'CND-101',
    title: 'Duplicate approval rules across submission paths',
    reviewStatus: 'awaiting_review',
    assetName: 'Harbor Intake',
    assetType: 'application',
    suggestedTeam: 'Workflow Enablement',
    context: {
      assetCriticality: 'high',
      dependencySummary: 'Used by 4 internal workflow integrations.',
    },
    evidence: [
      {
        id: 'EVD-101-A',
        sourceLabel: 'Static analysis',
        summary: 'Similar approval-rule branches appear in two submission modules.',
      },
      {
        id: 'EVD-101-B',
        sourceLabel: 'Change history',
        summary: 'The same rule set was updated separately across three recent changes.',
      },
      {
        id: 'EVD-101-C',
        sourceLabel: 'Architecture review',
        summary: 'Review notes identify parallel submission paths with overlapping responsibilities.',
      },
      {
        id: 'EVD-101-D',
        sourceLabel: 'Dependency inventory',
        summary: 'Multiple workflow integrations rely on the affected approval behavior.',
      },
    ],
  },
  {
    id: 'CND-102',
    title: 'Repeated exception handling in document intake',
    reviewStatus: 'needs_information',
    assetName: 'Cedar Documents',
    assetType: 'application',
    suggestedTeam: 'Document Services',
    context: {
      assetCriticality: 'medium',
      dependencySummary: 'Consumes documents from 2 internal intake channels.',
    },
    evidence: [
      {
        id: 'EVD-102-A',
        sourceLabel: 'Static analysis',
        summary: 'Matching exception-handling patterns occur in separate intake flows.',
      },
      {
        id: 'EVD-102-B',
        sourceLabel: 'Change history',
        summary: 'Recent changes modified the repeated handling independently.',
      },
    ],
  },
  {
    id: 'CND-103',
    title: 'Overlapping validation logic at service boundaries',
    reviewStatus: 'awaiting_review',
    assetName: 'Northstar Gateway',
    assetType: 'service',
    suggestedTeam: 'Integration Enablement',
    context: {
      assetCriticality: 'high',
      dependencySummary: 'Serves 5 internal service consumers.',
    },
    evidence: [
      {
        id: 'EVD-103-A',
        sourceLabel: 'Static analysis',
        summary: 'Validation checks overlap between request boundary handlers.',
      },
      {
        id: 'EVD-103-B',
        sourceLabel: 'Architecture review',
        summary: 'Service-boundary notes describe duplicated validation responsibility.',
      },
      {
        id: 'EVD-103-C',
        sourceLabel: 'Dependency inventory',
        summary: 'Several consumers depend on the affected request contract.',
      },
    ],
  },
  {
    id: 'CND-104',
    title: 'Inconsistent retention checks for archived records',
    reviewStatus: 'needs_information',
    assetName: 'Willow Archive',
    assetType: 'data_store',
    suggestedTeam: 'Information Stewardship',
    context: {
      assetCriticality: 'medium',
      dependencySummary: 'Supports 1 archive-processing workflow.',
    },
    evidence: [
      {
        id: 'EVD-104-A',
        sourceLabel: 'Static analysis',
        summary: 'Retention checks use inconsistent conditions in archival routines.',
      },
    ],
  },
  {
    id: 'CND-105',
    title: 'Repeated translation of common request fields',
    reviewStatus: 'awaiting_review',
    assetName: 'Beacon Exchange',
    assetType: 'service',
    suggestedTeam: 'Integration Enablement',
    context: {
      assetCriticality: 'medium',
      dependencySummary: 'Exchanges requests with 3 internal service consumers.',
    },
    evidence: [
      {
        id: 'EVD-105-A',
        sourceLabel: 'Static analysis',
        summary: 'Common request fields are translated in parallel service adapters.',
      },
      {
        id: 'EVD-105-B',
        sourceLabel: 'Architecture review',
        summary: 'Adapter boundaries contain repeated request-field mapping responsibilities.',
      },
    ],
  },
  {
    id: 'CND-106',
    title: 'Parallel formatting rules in correspondence templates',
    reviewStatus: 'needs_information',
    assetName: 'Meadow Notices',
    assetType: 'application',
    suggestedTeam: 'Communications Platform',
    context: {
      assetCriticality: 'low',
      dependencySummary: 'Supports 2 internal correspondence workflows.',
    },
    evidence: [
      {
        id: 'EVD-106-A',
        sourceLabel: 'Static analysis',
        summary: 'Formatting rules are repeated across correspondence templates.',
      },
      {
        id: 'EVD-106-B',
        sourceLabel: 'Change history',
        summary: 'Template updates changed parallel formatting rules separately.',
      },
    ],
  },
]

export function getMockCandidateDetail(id: string): CandidateDetailView | undefined {
  return mockCandidateDetails.find((candidate) => candidate.id === id)
}
