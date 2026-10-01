export type Classification =
  | "clean_success"
  | "recovered_success"
  | "fragile_success"
  | "rollback"
  | "failed";

export type RecoveryLoad = "low" | "medium" | "high" | "critical";
export type ToleranceLevel = "high" | "medium" | "low" | "critical";
export type Terminal = "succeeded" | "rolled_back" | "failed";

export interface DeploymentEvent {
  event_id: string;
  release_id: string;
  ts: string;
  type: string;
  actor: string;
  severity?: string;
  details?: Record<string, string | number | boolean>;
}

export interface ReleaseLog {
  schema_version: "1.0";
  release_id: string;
  service: string;
  window_minutes: number;
  retry_budget_max: number;
  events: DeploymentEvent[];
}

export interface BufferSnapshot {
  retries_used: number;
  retries_left: number;
  retry_reserve_pct: number;
  time_remaining_original_pct: number;
  time_remaining_effective_pct: number;
  extension_total_min: number;
  rollback_available: boolean;
  rollback_fresh: boolean;
  health_end: string;
  manual_count: number;
}

export interface Deduction {
  rule_id: string;
  event_ids: string[];
  points: number;
  reason: string;
}

export interface ScoreReport {
  reserve_level: number;
  recovery_load: RecoveryLoad;
  deductions: Deduction[];
  buffers: BufferSnapshot;
}

export interface RecoveryFollowUp {
  follow_up_id: string;
  kind: string;
  event_ids: string[];
  severity: string;
  required_action: string;
  status: string;
}

export interface RollbackSummary {
  executed: boolean;
  event_ids: string[];
  verified: boolean;
  manual: boolean;
}

export interface ToleranceReport {
  level: ToleranceLevel;
  retries_left: number;
  can_survive_second_failure: boolean;
  rationale: string[];
}

export interface ReleaseReport {
  release_id: string;
  classification: Classification;
  terminal: Terminal;
  score: ScoreReport;
  follow_ups: RecoveryFollowUp[];
  rollback_summary: RollbackSummary;
  tolerance: ToleranceReport;
}

export interface DemoReleaseMeta {
  release_id: string;
  display_name: string;
  classification_hint: Classification;
}

export interface PublicRepoMeta {
  repo_full_name: string;
  display_name: string;
  repo_url: string;
}

export interface CandidateInfo {
  candidate_id: string;
  kind: string;
  name: string;
  published_at: string | null;
  url: string;
}

export interface CommitRef {
  sha: string;
  message: string;
  date: string | null;
  url: string;
}

export interface PullRef {
  number: number;
  title: string;
  state: string;
  url: string;
}

export interface IssueRef {
  number: number;
  title: string;
  url: string;
}

export interface RepositoryEvidence {
  repo_full_name: string;
  repo_url: string;
  default_branch: string;
  stars: number;
  open_issues_count: number;
  candidate: CandidateInfo;
  candidates_available: CandidateInfo[];
  commits_recent: CommitRef[];
  pulls_recent: PullRef[];
  issues_open_sample: IssueRef[];
  retrieved_at: string;
  source_urls: string[];
}

export interface PublicResult {
  change_risk_level: string;
  evidence_completeness: string;
  deployment_readiness: string;
  public_recommendation: string;
  reasons: string[];
}

export interface PublicDataAssessment {
  data_source: string;
  served_from: string;
  repo_full_name: string;
  candidate: CandidateInfo;
  retrieved_at: string;
  source_urls: string[];
  limitations: string[];
  unavailable_signals: string[];
  disclaimer: string;
  public_result: PublicResult;
  evidence: RepositoryEvidence;
}
