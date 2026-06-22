import { NextResponse } from "next/server";

import { loadAgentRunTrace } from "../../../../lib/api";

type RouteContext = {
  params: Promise<{
    jobId: string;
  }>;
};

export async function GET(_request: Request, context: RouteContext) {
  const { jobId } = await context.params;
  const result = await loadAgentRunTrace(jobId);

  if (!result.ok) {
    return NextResponse.json(
      { message: result.message },
      { status: result.message === "Agent run not found." ? 404 : 502 },
    );
  }

  return NextResponse.json(result.trace);
}
