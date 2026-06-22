"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock3,
  FileText,
  GitBranch,
  RefreshCw,
  Search,
  Send,
} from "lucide-react";
import type { ReactNode } from "react";

import { loadAgentRunTraceFromClient } from "../lib/client-api";
import type { TraceLoadResult } from "../lib/api";
import type {
  AgentDecision,
  AgentPlan,
  AgentRunJob,
  AgentStep,
  FinalResult,
  TailoringAttempt,
} from "../lib/types";

const TRACE_REFETCH_INTERVAL_MS = 2500;

type AgentRunWorkspaceProps = {
  jobId: string;
  runError: string;
  initialTraceResult: TraceLoadResult | null;
};

export function AgentRunWorkspace({
  jobId,
  runError,
  initialTraceResult,
}: AgentRunWorkspaceProps) {
  const traceQuery = useQuery<TraceLoadResult>({
    queryKey: ["agent-run-trace", jobId],
    queryFn: () => loadAgentRunTraceFromClient(jobId),
    enabled: Boolean(jobId),
    initialData: initialTraceResult ?? undefined,
    refetchInterval: (query) =>
      shouldPollTrace(query.state.data) ? TRACE_REFETCH_INTERVAL_MS : false,
    refetchOnWindowFocus: true,
  });
  const traceResult = traceQuery.data ?? initialTraceResult;
  const lastUpdated = lastUpdatedLabel(traceQuery.dataUpdatedAt);
  const isPolling = shouldPollTrace(traceResult);

  return (
    <main className="shell">
      <section className="workspace">
        <aside className="sidePanel">
          <div>
            <p className="eyebrow">Agentic Resume</p>
            <h1>Agent Run Trace</h1>
          </div>

          <CreateRunForm errorMessage={runError} />

          <form className="lookupForm" action="/" method="get">
            <label htmlFor="jobId">Job ID</label>
            <div className="lookupRow">
              <input
                id="jobId"
                name="jobId"
                type="text"
                defaultValue={jobId}
                autoComplete="off"
              />
              <button type="submit" aria-label="Load trace">
                <Search aria-hidden="true" size={18} />
              </button>
            </div>
          </form>

          {traceResult?.ok ? (
            <JobSummary
              job={traceResult.trace.job}
              isFetching={traceQuery.isFetching}
              isPolling={isPolling}
              lastUpdated={lastUpdated}
            />
          ) : (
            <RuntimeSummary />
          )}
        </aside>

        <section className="tracePanel">
          {!jobId ? (
            <EmptyTraceState />
          ) : traceResult?.ok ? (
            <TraceView
              job={traceResult.trace.job}
              plan={traceResult.trace.plan}
              steps={traceResult.trace.steps}
              decisions={traceResult.trace.decisions}
              attempts={traceResult.trace.attempts}
              finalResult={traceResult.trace.final_result}
              isFetching={traceQuery.isFetching}
              isPolling={isPolling}
              lastUpdated={lastUpdated}
            />
          ) : (
            <ErrorState message={traceResult?.message ?? "Trace unavailable."} />
          )}
        </section>
      </section>
    </main>
  );
}

function CreateRunForm({ errorMessage }: { errorMessage: string }) {
  return (
    <form className="createForm" action="/agent-runs" method="post">
      <div className="formTitleRow">
        <FileText aria-hidden="true" size={18} />
        <h2>Create Run</h2>
      </div>

      {errorMessage ? (
        <p className="feedbackBanner" role="alert">
          {errorMessage}
        </p>
      ) : null}

      <label htmlFor="resumeText">Resume Text</label>
      <textarea id="resumeText" name="resumeText" rows={7} required />

      <label htmlFor="jobDescriptionText">Job Description</label>
      <textarea
        id="jobDescriptionText"
        name="jobDescriptionText"
        rows={7}
        required
      />

      <div className="compactField">
        <label htmlFor="maxAttempts">Max Attempts</label>
        <select id="maxAttempts" name="maxAttempts" defaultValue="2">
          <option value="1">1</option>
          <option value="2">2</option>
          <option value="3">3</option>
        </select>
      </div>

      <button className="primaryButton" type="submit">
        <Send aria-hidden="true" size={16} />
        <span>Create Run</span>
      </button>
    </form>
  );
}

function RuntimeSummary() {
  return (
    <div className="summaryBlock">
      <div className="summaryItem">
        <span>Backend</span>
        <strong>FastAPI</strong>
      </div>
      <div className="summaryItem">
        <span>Queue</span>
        <strong>RQ / Redis</strong>
      </div>
      <div className="summaryItem">
        <span>Trace Store</span>
        <strong>PostgreSQL</strong>
      </div>
    </div>
  );
}

function JobSummary({
  job,
  isFetching,
  isPolling,
  lastUpdated,
}: {
  job: AgentRunJob;
  isFetching: boolean;
  isPolling: boolean;
  lastUpdated: string;
}) {
  return (
    <div className="summaryBlock">
      <div className="summaryItem">
        <span>Status</span>
        <StatusBadge status={job.status} />
      </div>
      <div className="summaryItem">
        <span>Monitor</span>
        <strong>{monitorLabel({ isFetching, isPolling })}</strong>
      </div>
      <div className="summaryItem">
        <span>Updated</span>
        <strong>{lastUpdated}</strong>
      </div>
      <div className="summaryItem">
        <span>Run ID</span>
        <strong>{job.run_id ?? "pending"}</strong>
      </div>
      <div className="summaryItem">
        <span>RQ Job</span>
        <strong>{job.rq_job_id ?? "not queued"}</strong>
      </div>
      {job.error_message ? (
        <div className="summaryItem errorText">
          <span>Error</span>
          <strong>{job.error_message}</strong>
        </div>
      ) : null}
    </div>
  );
}

function EmptyTraceState() {
  return (
    <div className="emptyState">
      <Activity aria-hidden="true" size={32} />
      <h2>No Run Selected</h2>
      <p>Trace data appears here after selecting an agent run.</p>
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="emptyState errorState">
      <AlertTriangle aria-hidden="true" size={32} />
      <h2>Trace Unavailable</h2>
      <p>{message}</p>
    </div>
  );
}

function TraceView({
  job,
  plan,
  steps,
  decisions,
  attempts,
  finalResult,
  isFetching,
  isPolling,
  lastUpdated,
}: {
  job: AgentRunJob;
  plan: AgentPlan | null;
  steps: AgentStep[];
  decisions: AgentDecision[];
  attempts: TailoringAttempt[];
  finalResult: FinalResult | null;
  isFetching: boolean;
  isPolling: boolean;
  lastUpdated: string;
}) {
  return (
    <div className="traceStack">
      <LiveMonitorBar
        job={job}
        isFetching={isFetching}
        isPolling={isPolling}
        lastUpdated={lastUpdated}
      />

      <section className="sectionBand">
        <SectionHeader icon={<GitBranch size={18} />} title="Plan" />
        {plan ? <PlanView plan={plan} /> : <PendingTrace />}
      </section>

      <section className="sectionBand">
        <SectionHeader icon={<Activity size={18} />} title="Steps" />
        {steps.length ? <StepsTable steps={steps} /> : <PendingTrace />}
      </section>

      <section className="sectionBand twoColumn">
        <div>
          <SectionHeader icon={<RefreshCw size={18} />} title="Decisions" />
          {decisions.length ? (
            <DecisionList decisions={decisions} />
          ) : (
            <PendingTrace />
          )}
        </div>
        <div>
          <SectionHeader icon={<Clock3 size={18} />} title="Attempts" />
          {attempts.length ? (
            <AttemptList attempts={attempts} />
          ) : (
            <PendingTrace />
          )}
        </div>
      </section>

      <section className="sectionBand">
        <SectionHeader icon={<FileText size={18} />} title="Final Result" />
        {finalResult ? (
          <FinalResultView finalResult={finalResult} />
        ) : (
          <PendingTrace />
        )}
      </section>
    </div>
  );
}

function LiveMonitorBar({
  job,
  isFetching,
  isPolling,
  lastUpdated,
}: {
  job: AgentRunJob;
  isFetching: boolean;
  isPolling: boolean;
  lastUpdated: string;
}) {
  return (
    <section className="monitorBar">
      <div>
        <span className="sectionIcon">
          <RefreshCw aria-hidden="true" size={18} />
        </span>
        <div>
          <h2>Live Monitor</h2>
          <p>{monitorLabel({ isFetching, isPolling })}</p>
        </div>
      </div>
      <div className="monitorMeta">
        <StatusBadge status={job.status} />
        <span>{lastUpdated}</span>
      </div>
    </section>
  );
}

function SectionHeader({
  icon,
  title,
}: {
  icon: ReactNode;
  title: string;
}) {
  return (
    <div className="sectionHeader">
      <span className="sectionIcon">{icon}</span>
      <h2>{title}</h2>
    </div>
  );
}

function PlanView({ plan }: { plan: AgentPlan }) {
  return (
    <div className="planGrid">
      <div className="metric">
        <span>Plan ID</span>
        <strong>{plan.plan_id}</strong>
      </div>
      <div className="metric">
        <span>Orchestrator</span>
        <strong>{plan.orchestrator_agent}</strong>
      </div>
      <div className="metric">
        <span>Max Iterations</span>
        <strong>{plan.max_iterations ?? "unbounded"}</strong>
      </div>
      <div className="planItems">
        {plan.items.map((item) => (
          <div className="planItem" key={item.step_id}>
            <div>
              <strong>{item.agent_name}</strong>
              <span>{item.tool_name}</span>
            </div>
            <RoleBadge role={item.role} />
          </div>
        ))}
      </div>
    </div>
  );
}

function StepsTable({ steps }: { steps: AgentStep[] }) {
  return (
    <div className="tableWrap">
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>Agent</th>
            <th>Role</th>
            <th>Tool</th>
            <th>Status</th>
            <th>Attempt</th>
            <th>Output</th>
          </tr>
        </thead>
        <tbody>
          {steps.map((step) => (
            <tr key={`${step.step_number}-${step.tool_name}`}>
              <td>{step.step_number}</td>
              <td>{step.agent_name}</td>
              <td>
                <RoleBadge role={step.role} />
              </td>
              <td>{step.tool_name}</td>
              <td>
                <StatusBadge status={step.status} />
              </td>
              <td>{step.attempt_number ?? "-"}</td>
              <td>{step.output_summary ?? step.message ?? "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DecisionList({ decisions }: { decisions: AgentDecision[] }) {
  return (
    <div className="listStack">
      {decisions.map((decision) => (
        <div className="listItem" key={decision.decision_number}>
          <div className="listItemHeader">
            <strong>
              {decision.decision_number}. {decision.decision_type}
            </strong>
            <span>{decision.next_agent ?? "terminal"}</span>
          </div>
          <p>{decision.reason}</p>
          {decision.feedback_issue_count ? (
            <small>{decision.feedback_issue_count} feedback issues</small>
          ) : null}
        </div>
      ))}
    </div>
  );
}

function AttemptList({ attempts }: { attempts: TailoringAttempt[] }) {
  return (
    <div className="listStack">
      {attempts.map((attempt) => (
        <div className="listItem" key={attempt.attempt_number}>
          <div className="listItemHeader">
            <strong>Attempt {attempt.attempt_number}</strong>
            <StatusBadge status={attempt.status} />
          </div>
          <p>{attempt.message ?? "No attempt message."}</p>
          <small>
            {attempt.rewrite_suggestions.length} rewrites ·{" "}
            {attempt.validation_issues.length} issues
          </small>
        </div>
      ))}
    </div>
  );
}

function FinalResultView({ finalResult }: { finalResult: FinalResult }) {
  const suggestions = finalResult.rewrite_suggestions ?? [];
  const issues = finalResult.validation_issues ?? [];

  return (
    <div className="finalGrid">
      <div className="metric">
        <span>Status</span>
        <StatusBadge status={finalResult.status} />
      </div>
      <div className="metric">
        <span>Role</span>
        <strong>{finalResult.job_analysis?.job_title ?? "untitled"}</strong>
      </div>
      <div className="metric">
        <span>Rewrites</span>
        <strong>{suggestions.length}</strong>
      </div>
      <div className="metric">
        <span>Issues</span>
        <strong>{issues.length}</strong>
      </div>
      <div className="rewriteList">
        {suggestions.map((suggestion) => (
          <div className="rewriteItem" key={suggestion.bullet_id}>
            <strong>{suggestion.bullet_id}</strong>
            <p>{suggestion.rewritten_text}</p>
            <small>{suggestion.requirement_ids.join(", ")}</small>
          </div>
        ))}
      </div>
    </div>
  );
}

function PendingTrace() {
  return <p className="muted">Pending trace data.</p>;
}

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`badge status-${normalizeClassName(status)}`}>
      {status === "success" || status === "succeeded" || status === "accepted" ? (
        <CheckCircle2 aria-hidden="true" size={14} />
      ) : null}
      {status}
    </span>
  );
}

function RoleBadge({ role }: { role: string }) {
  return <span className={`roleBadge role-${normalizeClassName(role)}`}>{role}</span>;
}

function shouldPollTrace(result: TraceLoadResult | undefined | null): boolean {
  return result?.ok ? isActiveJobStatus(result.trace.job.status) : false;
}

function isActiveJobStatus(status: string): boolean {
  return status === "queued" || status === "running";
}

function lastUpdatedLabel(dataUpdatedAt: number): string {
  if (!dataUpdatedAt) {
    return "not synced";
  }

  return new Intl.DateTimeFormat(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(dataUpdatedAt);
}

function monitorLabel({
  isFetching,
  isPolling,
}: {
  isFetching: boolean;
  isPolling: boolean;
}): string {
  if (isFetching) {
    return "refreshing";
  }
  if (isPolling) {
    return "watching active run";
  }
  return "terminal";
}

function normalizeClassName(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-");
}
