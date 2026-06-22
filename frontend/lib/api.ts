import type { AgentRunJob, AgentRunTrace, CreateAgentRunInput } from "./types";

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

export type CreateAgentRunResult =
  | {
      ok: true;
      job: AgentRunJob;
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

export async function createAgentRun(
  input: CreateAgentRunInput,
): Promise<CreateAgentRunResult> {
  try {
    const response = await fetch(`${API_URL}/agent-runs`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        resume_text: input.resumeText,
        job_description_text: input.jobDescriptionText,
        max_attempts: input.maxAttempts,
      }),
    });

    if (!response.ok) {
      return {
        ok: false,
        message: await errorMessageFromResponse(response),
      };
    }

    return {
      ok: true,
      job: (await response.json()) as AgentRunJob,
    };
  } catch (error) {
    return {
      ok: false,
      message:
        error instanceof Error ? error.message : "Agent run request failed.",
    };
  }
}

async function errorMessageFromResponse(response: Response): Promise<string> {
  const fallback = `Agent run request failed with status ${response.status}.`;

  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string") {
      return payload.detail;
    }
  } catch {
    return fallback;
  }

  return fallback;
}
