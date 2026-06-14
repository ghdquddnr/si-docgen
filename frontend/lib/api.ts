// 백엔드 API 타입 클라이언트. 컴포넌트에서 fetch 를 직접 부르지 않고 이 모듈만 사용한다.

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export type JobStatus = "pending" | "running" | "succeeded" | "failed";

export interface Job {
  id: string;
  status: JobStatus;
  input_filename: string;
  project_name: string;
  system_name: string;
  author: string;
  written_date: string;
  with_screens: boolean;
  with_requirements: boolean;
  error: string | null;
  created_at: string;
}

export interface CreateJobOptions {
  withScreens?: boolean;
  withRequirements?: boolean;
  requirementSpecModel?: string;
  scenarioModel?: string;
  screenSpecModel?: string;
}

export interface CoverInfo {
  project_name: string;
  system_name: string;
  author: string;
  written_date: string;
}

export interface RenderResult {
  unit_count: number;
  integration_count: number;
  requirement_count: number;
  downloads: Record<string, string>;
}

export type TestResult = "Pass" | "Fail" | null;

export interface TestCase {
  tc_id: string;
  req_id: string;
  category_major: string;
  category_minor: string;
  scenario_name: string;
  precondition: string;
  test_steps: string[];
  expected_result: string;
  result: TestResult;
  note: string;
}

export interface Scenario {
  project_name: string;
  system_name: string;
  author: string;
  written_date: string;
  unit_test_cases: TestCase[];
  integration_test_cases: TestCase[];
}

export type CaseListKey = "unit_test_cases" | "integration_test_cases";

// SSE 진행 이벤트 페이로드
export interface ProgressEvent {
  status: JobStatus;
  progress: string | null;
  error: string | null;
  terminal: boolean;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function parse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail: string = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body);
    } catch {
      // 본문이 JSON 이 아니면 statusText 유지
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export async function createJob(
  file: File,
  cover: CoverInfo,
  opts: CreateJobOptions = {},
): Promise<Job> {
  const form = new FormData();
  form.append("file", file);
  form.append("project_name", cover.project_name);
  form.append("system_name", cover.system_name);
  form.append("author", cover.author);
  form.append("written_date", cover.written_date);
  form.append("with_screens", String(opts.withScreens ?? false));
  form.append("with_requirements", String(opts.withRequirements ?? false));
  if (opts.requirementSpecModel) form.append("requirement_spec_model", opts.requirementSpecModel);
  if (opts.scenarioModel) form.append("scenario_model", opts.scenarioModel);
  if (opts.screenSpecModel) form.append("screen_spec_model", opts.screenSpecModel);
  return parse<Job>(await fetch(`${API_BASE}/jobs`, { method: "POST", body: form }));
}

export async function getJob(id: string): Promise<Job> {
  return parse<Job>(await fetch(`${API_BASE}/jobs/${id}`));
}

export async function getScenario(id: string): Promise<Scenario> {
  return parse<Scenario>(await fetch(`${API_BASE}/jobs/${id}/scenario`));
}

export async function putScenario(id: string, scenario: Scenario): Promise<Job> {
  return parse<Job>(
    await fetch(`${API_BASE}/jobs/${id}/scenario`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(scenario),
    }),
  );
}

export async function renderJob(id: string): Promise<RenderResult> {
  return parse<RenderResult>(await fetch(`${API_BASE}/jobs/${id}/render`, { method: "POST" }));
}

export function eventsUrl(id: string): string {
  return `${API_BASE}/jobs/${id}/events`;
}

export function downloadUrl(id: string, kind: string): string {
  return `${API_BASE}/jobs/${id}/download/${kind}`;
}
