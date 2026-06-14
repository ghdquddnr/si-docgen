import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import Link from "next/link";

export type NodeStatus = "idle" | "running" | "done" | "error";

const DOT: Record<NodeStatus, string> = {
  idle: "bg-slate-300",
  running: "bg-indigo-500 animate-pulse",
  done: "bg-emerald-500",
  error: "bg-red-500",
};
const RING: Record<NodeStatus, string> = {
  idle: "border-slate-200",
  running: "border-indigo-400 ring-2 ring-indigo-100",
  done: "border-emerald-300",
  error: "border-red-300",
};

export const MODEL_PRESETS = [
  { value: "", label: "기본 (설정값)" },
  { value: "ollama/gemma4:e4b", label: "gemma4:e4b (로컬)" },
  { value: "ollama/gemma4:12b", label: "gemma4:12b (로컬)" },
  { value: "ollama/qwen3:14b", label: "qwen3:14b (로컬)" },
  { value: "anthropic/claude-sonnet-4-6", label: "claude-sonnet (상용)" },
];

function shell(status: NodeStatus): string {
  return `w-60 rounded-xl border bg-white px-4 py-3 shadow-sm ${RING[status]}`;
}

function header(title: string, status: NodeStatus, accent?: boolean) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="flex items-center gap-1.5 text-sm font-semibold text-slate-800">
        {accent && <span className="text-indigo-500">✦</span>}
        {title}
      </span>
      <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${DOT[status]}`} />
    </div>
  );
}

// ── 원천 문서 노드 (파일 업로드)
export interface SourceNodeData extends Record<string, unknown> {
  filename: string | null;
  onPick: (f: File | null) => void;
  status: NodeStatus;
  disabled: boolean;
}
export type SourceNodeType = Node<SourceNodeData, "source">;

export function SourceNode({ data }: NodeProps<SourceNodeType>) {
  return (
    <div className={shell(data.status)}>
      {header("원천 문서", data.status)}
      <label className="nodrag mt-2 block cursor-pointer rounded-lg border border-dashed border-slate-300 bg-slate-50 px-2 py-2 text-center text-xs text-slate-500 hover:border-indigo-400">
        {data.filename ?? "클릭하여 파일 선택"}
        <input
          type="file"
          accept=".docx,.pdf,.md,.markdown,.txt"
          disabled={data.disabled}
          onChange={(e) => data.onPick(e.target.files?.[0] ?? null)}
          className="hidden"
        />
      </label>
      <Handle type="source" position={Position.Right} className="!h-2 !w-2 !bg-slate-300" />
    </div>
  );
}

// ── LLM 생성 노드 (모델 선택)
export interface LlmNodeData extends Record<string, unknown> {
  title: string;
  status: NodeStatus;
  model: string;
  onModel: (m: string) => void;
  disabled: boolean;
}
export type LlmNodeType = Node<LlmNodeData, "llm">;

export function LlmNode({ data }: NodeProps<LlmNodeType>) {
  return (
    <div className={shell(data.status)}>
      <Handle type="target" position={Position.Left} className="!h-2 !w-2 !bg-slate-300" />
      {header(data.title, data.status, true)}
      <p className="mt-0.5 text-xs text-slate-400">LLM 생성</p>
      <select
        value={data.model}
        disabled={data.disabled}
        onChange={(e) => data.onModel(e.target.value)}
        className="nodrag mt-2 w-full rounded-md border border-slate-300 bg-white px-2 py-1 text-xs text-slate-700 focus:border-indigo-400 focus:outline-none disabled:opacity-60"
      >
        {MODEL_PRESETS.map((m) => (
          <option key={m.value} value={m.value}>
            {m.label}
          </option>
        ))}
      </select>
      <Handle type="source" position={Position.Right} className="!h-2 !w-2 !bg-slate-300" />
    </div>
  );
}

// ── 결과(RTM) 노드 — 완료 시 검수/다운로드
export interface OutputNodeData extends Record<string, unknown> {
  status: NodeStatus;
  jobId: string | null;
  downloads: Record<string, string> | null;
  onRender: () => void;
  rendering: boolean;
}
export type OutputNodeType = Node<OutputNodeData, "output">;

const DOWNLOAD_LABEL: Record<string, string> = {
  requirement_spec: "요구사항정의서",
  test_scenario: "테스트시나리오",
  rtm: "요건추적표",
  screen_spec: "화면정의서",
  wbs: "WBS",
  table_spec: "테이블정의서",
};

export function OutputNode({ data }: NodeProps<OutputNodeType>) {
  const done = data.status === "done";
  return (
    <div className={shell(data.status)}>
      <Handle type="target" position={Position.Left} className="!h-2 !w-2 !bg-slate-300" />
      {header("요건추적표(RTM)", data.status)}
      <p className="mt-0.5 text-xs text-slate-400">REQ→SCR→TC 자동 연결</p>

      {done && data.jobId && (
        <div className="nodrag mt-2 flex flex-col gap-1.5">
          <Link
            href={`/jobs/${data.jobId}`}
            className="rounded-md bg-indigo-600 px-2 py-1 text-center text-xs font-medium text-white hover:bg-indigo-700"
          >
            검수 화면으로 →
          </Link>
          {data.downloads ? (
            <div className="flex flex-col gap-1">
              {Object.entries(data.downloads).map(([kind, path]) => (
                <a
                  key={kind}
                  href={`${process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000"}${path}`}
                  className="rounded-md border border-emerald-300 px-2 py-1 text-center text-xs text-emerald-700 hover:bg-emerald-50"
                >
                  ↓ {DOWNLOAD_LABEL[kind] ?? kind}
                </a>
              ))}
            </div>
          ) : (
            <button
              onClick={data.onRender}
              disabled={data.rendering}
              className="rounded-md border border-slate-300 px-2 py-1 text-xs text-slate-600 hover:bg-slate-50 disabled:opacity-50"
            >
              {data.rendering ? "렌더링 중…" : "렌더링하여 다운로드"}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
