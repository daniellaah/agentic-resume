import type { TraceLoadResult } from "./api";
import type { AgentRunTrace } from "./types";

export async function loadAgentRunTraceFromClient(
  jobId: string,
): Promise<TraceLoadResult> {
  const normalizedJobId = jobId.trim();
  if (!normalizedJobId) {
    return {
      ok: false,
      message: "Missing job id.",
    };
  }

  try {
    const response = await fetch(
      `/agent-runs/${encodeURIComponent(normalizedJobId)}/trace`,
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
        message: await errorMessageFromResponse(response),
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

async function errorMessageFromResponse(response: Response): Promise<string> {
  const fallback = `Trace request failed with status ${response.status}.`;

  try {
    const payload = (await response.json()) as { message?: unknown };
    if (typeof payload.message === "string") {
      return payload.message;
    }
  } catch {
    return fallback;
  }

  return fallback;
}
