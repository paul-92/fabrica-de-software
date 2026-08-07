export type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue };

export type AIRuntimeConnectionState = "not_installed" | "not_authenticated" | "ready" | "error";
export type AIRuntimeExecutionMode = "read_only" | "workspace_write";
export type WorkspaceChangeDto = Readonly<{
  path: string;
  change_type: "created" | "modified" | "deleted";
  size_before: number | null;
  size_after: number | null;
}>;
export type AIRuntimeStatusDto = Readonly<{
  runtime_id: string;
  installed: boolean;
  authenticated: boolean;
  ready: boolean;
  state: AIRuntimeConnectionState;
  version: string | null;
  message: string;
  authentication_command: string | null;
}>;
export type ProjectAIRuntimeExecutionDto = Readonly<{
  execution_id: string;
  output: string;
  runtime_id: string;
  model_id: string;
  usage: Readonly<{
    input_units: number | null;
    output_units: number | null;
    total_units: number | null;
    cost: number | null;
  }> | null;
  metadata: Record<string, JsonValue>;
  execution_mode: AIRuntimeExecutionMode;
  changes: readonly WorkspaceChangeDto[];
}>;

export type ProjectSessionDto = Readonly<{
  session_id: string;
  project_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}>;

export type ProjectExecutionDto = Readonly<{
  execution_id: string;
  session_id: string;
  project_id: string;
  runtime_id: string;
  instruction: string;
  execution_mode: AIRuntimeExecutionMode;
  status: "pending" | "running" | "succeeded" | "failed";
  output: string | null;
  model: string | null;
  usage: ProjectAIRuntimeExecutionDto["usage"];
  changes: readonly WorkspaceChangeDto[];
  error_code: string | null;
  created_at: string;
  completed_at: string | null;
}>;

export type ProjectDto = Readonly<{
  project_id: string;
  name: string;
  workspace_path: string;
  created_at: string;
  updated_at: string;
}>;

export type CreateProjectDto = Readonly<{
  name: string;
  workspace_path: string;
}>;

export type MemoryEntryDto = Readonly<{
  memory_id: string;
  agent_id: string;
  execution_id: string;
  workflow_execution_id?: string | null;
  category: "fact" | "decision" | "observation" | "plan" | "task" | "error" | "result" | "system" | "custom";
  importance: 1 | 2 | 3 | 4;
  content: string;
  metadata?: Record<string, JsonValue>;
  created_at: string;
  updated_at: string;
  expires_at?: string | null;
}>;

export type PlanningContextDto = Readonly<{
  objective: string;
  memory?: readonly MemoryEntryDto[];
  workflow?: Record<string, JsonValue>;
  metadata?: Record<string, JsonValue>;
  constraints?: readonly string[];
  available_capabilities?: readonly string[];
  available_tools?: Readonly<Record<string, string>>;
}>;

export type PlanningRequestDto = Readonly<{
  goal: string;
  context: PlanningContextDto;
  workflow_execution_id?: string | null;
  agent_id?: string | null;
  metadata?: Record<string, JsonValue>;
}>;

export type KnowledgeAwareContextDto = Readonly<{
  base_context?: Record<string, JsonValue>;
  learned_entries?: readonly MemoryEntryDto[];
  knowledge_count: number;
  metadata?: Record<string, JsonValue>;
}>;

export type FailureAnalysisDto = Readonly<{
  summary: string;
  failure_output?: string;
  affected_paths?: readonly string[];
  probable_cause?: string | null;
}>;

export type AutonomousEngineeringRequestDto = Readonly<{
  analysis: FailureAnalysisDto;
  replacement_contents: Readonly<Record<string, string>>;
  test_paths?: readonly string[];
}>;

export type IntelligentEngineeringRequestDto = Readonly<{
  planning_request: PlanningRequestDto;
  knowledge_context: KnowledgeAwareContextDto;
  engineering_request: AutonomousEngineeringRequestDto;
}>;

export type PlanStepDto = Readonly<{
  step_id: string;
  description: string;
  required_capability: string;
  tool_id: string | null;
  agent_id: string | null;
  dependencies: readonly string[];
  priority: number;
  status: string;
  estimated_cost: number;
  estimated_duration_seconds: number;
  metadata: Record<string, JsonValue>;
}>;

export type PlanningResultDto = Readonly<{
  plan: {
    plan_id: string;
    goal: string;
    steps: readonly PlanStepDto[];
    estimated_cost: number;
    estimated_duration_seconds: number;
    created_at: string;
    metadata: Record<string, JsonValue>;
  };
  warnings: readonly string[];
  validation_messages: readonly string[];
  statistics: {
    total_steps: number;
    dependency_count: number;
    maximum_depth: number;
    estimated_cost: number;
    estimated_duration_seconds: number;
    memory_entries_considered: number;
  };
}>;

export type RepairChangeDto = Readonly<{ path: string; content: string; overwrite: boolean; reason: string }>;
export type RepairPlanDto = Readonly<{
  analysis: FailureAnalysisDto;
  changes: readonly RepairChangeDto[];
  test_paths: readonly string[];
}>;
export type RepairResultDto = Readonly<{
  status: string;
  attempts: readonly {
    attempt: number;
    plan: RepairPlanDto;
    status: string;
    validation_output: string;
    messages: readonly string[];
  }[];
  final_analysis: FailureAnalysisDto | null;
  messages: readonly string[];
}>;

export type AutonomousEngineeringResultDto = Readonly<{
  proposal: {
    summary: string;
    reasoning: string;
    candidate_files: readonly string[];
    suggested_actions: readonly string[];
    confidence: number;
  };
  plan: RepairPlanDto;
  repair_result: RepairResultDto;
  reflection: {
    summary: string;
    outcome: string;
    lessons: readonly string[];
    recommended_actions: readonly string[];
    should_retry: boolean;
    confidence: number;
  };
}>;

export type IntelligentEngineeringResponseDto = Readonly<{
  planning_request: PlanningRequestDto;
  planning_result: PlanningResultDto;
  engineering_result: AutonomousEngineeringResultDto;
}>;

export type RunDto = Readonly<{
  id: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  project_id: string | null;
  workflow_id: string | null;
  stage_id: string | null;
  provider_name: string | null;
  summary: string | null;
  error: { type: string; message: string; details: Record<string, JsonValue> } | null;
  metadata: Record<string, JsonValue>;
}>;

export type TimelineEventDto = Readonly<{
  id: string;
  run_id: string;
  timestamp: string;
  type: string;
  stage_id: string | null;
  message: string | null;
  metadata: Record<string, JsonValue>;
}>;

export type DurationMetricsDto = Readonly<{
  count: number;
  ignored_count: number;
  minimum_seconds: number | null;
  maximum_seconds: number | null;
  average_seconds: number | null;
  median_seconds: number | null;
}>;

export type MetricsSummaryDto = Readonly<{
  total_runs: number;
  successful_runs: number;
  failed_runs: number;
  running_runs: number;
  pending_runs: number;
  cancelled_runs: number;
  unknown_status_runs: number;
  eligible_runs: number;
  success_rate: number;
  failure_rate: number;
  duration: DurationMetricsDto;
}>;

export type StatusMetricDto = Readonly<{ status: string; count: number }>;
export type ProviderMetricDto = Readonly<{
  provider_name: string | null;
  total_runs: number;
  successful_runs: number;
  failed_runs: number;
  running_runs: number;
  unknown_status_runs: number;
  eligible_runs: number;
  success_rate: number;
  failure_rate: number;
  duration: DurationMetricsDto;
}>;
