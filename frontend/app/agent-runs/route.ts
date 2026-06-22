import { type NextRequest, NextResponse } from "next/server";

import { createAgentRun } from "../../lib/api";

export async function POST(request: NextRequest) {
  const formData = await request.formData();
  const resumeText = stringFromFormValue(formData.get("resumeText"));
  const jobDescriptionText = stringFromFormValue(
    formData.get("jobDescriptionText"),
  );
  const maxAttempts = maxAttemptsFromFormValue(formData.get("maxAttempts"));

  if (!resumeText.trim() || !jobDescriptionText.trim()) {
    return redirectWithCreateError(request, "Resume and job description are required.");
  }

  const result = await createAgentRun({
    resumeText,
    jobDescriptionText,
    maxAttempts,
  });

  if (!result.ok) {
    return redirectWithCreateError(request, result.message);
  }

  const url = new URL("/", request.url);
  url.searchParams.set("jobId", result.job.job_id);
  return NextResponse.redirect(url, 303);
}

function stringFromFormValue(value: FormDataEntryValue | null): string {
  return typeof value === "string" ? value : "";
}

function maxAttemptsFromFormValue(value: FormDataEntryValue | null): number {
  const parsed = Number.parseInt(stringFromFormValue(value), 10);
  if (Number.isNaN(parsed)) {
    return 2;
  }
  return Math.min(Math.max(parsed, 1), 3);
}

function redirectWithCreateError(request: NextRequest, message: string) {
  const url = new URL("/", request.url);
  url.searchParams.set("runError", message.slice(0, 240));
  return NextResponse.redirect(url, 303);
}
