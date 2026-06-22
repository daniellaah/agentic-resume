import { AgentRunWorkspace } from "./agent-run-workspace";
import { loadAgentRunTrace } from "../lib/api";

type PageProps = {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
};

export default async function Page({ searchParams }: PageProps) {
  const params = (await searchParams) ?? {};
  const jobId = valueFromSearchParam(params.jobId);
  const runError = valueFromSearchParam(params.runError);
  const initialTraceResult = jobId ? await loadAgentRunTrace(jobId) : null;

  return (
    <AgentRunWorkspace
      jobId={jobId}
      runError={runError}
      initialTraceResult={initialTraceResult}
    />
  );
}

function valueFromSearchParam(value: string | string[] | undefined): string {
  if (Array.isArray(value)) {
    return value[0] ?? "";
  }
  return value ?? "";
}
