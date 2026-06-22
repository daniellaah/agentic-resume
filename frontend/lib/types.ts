export type AgentRunJob = {
  job_id: string;
  rq_job_id: string | null;
  status: "queued" | "running" | "succeeded" | "failed" | string;
  run_id: string | null;
  error_message: string | null;
};

export type AgentPlanItem = {
  step_id: string;
  agent_name: string;
  role: string;
  tool_name: string;
  objective: string;
  depends_on: string[];
  optional: boolean;
  repeatable: boolean;
};

export type AgentPlan = {
  plan_id: string;
  orchestrator_agent: string;
  objective: string;
  max_iterations: number | null;
  items: AgentPlanItem[];
};

export type AgentStep = {
  step_number: number;
  agent_name: string;
  role: string;
  tool_name: string;
  status: string;
  input_summary: string | null;
  output_summary: string | null;
  message: string | null;
  attempt_number: number | null;
};

export type AgentDecision = {
  decision_number: number;
  agent_name: string;
  decision_type: string;
  reason: string;
  next_agent: string | null;
  attempt_number: number | null;
  feedback_issue_count: number;
};

export type TailoringAttempt = {
  attempt_number: number;
  status: string;
  rewrite_suggestions: unknown[];
  validation_issues: unknown[];
  message: string | null;
};

export type FinalResult = {
  status: string;
  rewrite_suggestions?: Array<{
    bullet_id: string;
    rewritten_text: string;
    requirement_ids: string[];
  }>;
  validation_issues?: Array<{
    issue_type: string;
    severity: string;
    message: string;
  }>;
  job_analysis?: {
    job_title: string | null;
    requirements: Array<{
      id: string;
      text: string;
      priority: string;
    }>;
  };
};

export type AgentRunTrace = {
  job: AgentRunJob;
  plan: AgentPlan | null;
  steps: AgentStep[];
  decisions: AgentDecision[];
  attempts: TailoringAttempt[];
  final_result: FinalResult | null;
};
