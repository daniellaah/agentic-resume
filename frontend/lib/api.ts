import type { AgentRunTrace } from "./types";

const API_URL = process.env.AGENTIC_RESUME_API_URL ?? "http://127.0.0.1:8000";

export type TraceLoadResult =
  | {
      ok: true;
      trace: AgentRunTrace;
    }
  | {
      ok: false;
      message: string;
    };

export async function loadAgentRunTrace(jobId: string): Promise<TraceLoadResult> {
  const normalizedJobId = jobId.trim();
  if (!normalizedJobId) {
    return {
      ok: false,
      message: "Missing job id.",
    };
  }

  try {
    const response = await fetch(
      `${API_URL}/agent-runs/${encodeURIComponent(normalizedJobId)}/trace`,
      {
        cache: "no-store",
      },
    );

    if (response.status === 404) {
      return {
        ok: false,
        message: "Agent run not found.",
      };
    }

    if (!response.ok) {
      return {
        ok: false,
        message: `Trace request failed with status ${response.status}.`,
      };
    }

    return {
      ok: true,
      trace: (await response.json()) as AgentRunTrace,
    };
  } catch (error) {
    return {
      ok: false,
      message: error instanceof Error ? error.message : "Trace request failed.",
    };
  }
}
