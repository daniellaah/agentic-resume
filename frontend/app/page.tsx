import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock3,
  FileText,
  GitBranch,
  RefreshCw,
  Search,
} from "lucide-react";
import type { ReactNode } from "react";

import { loadAgentRunTrace } from "../lib/api";
import type {
  AgentDecision,
  AgentPlan,
  AgentRunJob,
  AgentStep,
  FinalResult,
  TailoringAttempt,
} from "../lib/types";

type PageProps = {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
};

export default async function Page({ searchParams }: PageProps) {
  const params = (await searchParams) ?? {};
  const jobId = valueFromSearchParam(params.jobId);
  const traceResult = jobId ? await loadAgentRunTrace(jobId) : null;

  return (
    <main className="shell">
      <section className="workspace">
        <aside className="sidePanel">
          <div>
            <p className="eyebrow">Agentic Resume</p>
            <h1>Agent Run Trace</h1>
          </div>

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
            <JobSummary job={traceResult.trace.job} />
          ) : (
            <RuntimeSummary />
          )}
        </aside>

        <section className="tracePanel">
          {!jobId ? (
            <EmptyTraceState />
          ) : traceResult?.ok ? (
            <TraceView
              plan={traceResult.trace.plan}
              steps={traceResult.trace.steps}
              decisions={traceResult.trace.decisions}
              attempts={traceResult.trace.attempts}
              finalResult={traceResult.trace.final_result}
            />
          ) : (
            <ErrorState message={traceResult?.message ?? "Trace unavailable."} />
          )}
        </section>
      </section>
    </main>
  );
}

function valueFromSearchParam(value: string | string[] | undefined): string {
  if (Array.isArray(value)) {
    return value[0] ?? "";
  }
  return value ?? "";
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

function JobSummary({ job }: { job: AgentRunJob }) {
  return (
    <div className="summaryBlock">
      <div className="summaryItem">
        <span>Status</span>
        <StatusBadge status={job.status} />
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
  plan,
  steps,
  decisions,
  attempts,
  finalResult,
}: {
  plan: AgentPlan | null;
  steps: AgentStep[];
  decisions: AgentDecision[];
  attempts: TailoringAttempt[];
  finalResult: FinalResult | null;
}) {
  return (
    <div className="traceStack">
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

function normalizeClassName(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-");
}
