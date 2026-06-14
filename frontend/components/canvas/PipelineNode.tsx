import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";

export type NodeStatus = "idle" | "running" | "done" | "error";

export interface PipelineNodeData extends Record<string, unknown> {
  title: string;
  subtitle: string;
  status?: NodeStatus;
  accent?: boolean; // LLM 노드 강조
}

export type PipelineNodeType = Node<PipelineNodeData, "pipeline">;

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

export default function PipelineNode({ data }: NodeProps<PipelineNodeType>) {
  const status = data.status ?? "idle";
  return (
    <div className={`w-52 rounded-xl border bg-white px-4 py-3 shadow-sm ${RING[status]}`}>
      <Handle type="target" position={Position.Left} className="!h-2 !w-2 !bg-slate-300" />
      <div className="flex items-center justify-between gap-2">
        <span className="flex items-center gap-1.5 text-sm font-semibold text-slate-800">
          {data.accent && <span className="text-indigo-500">✦</span>}
          {data.title}
        </span>
        <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${DOT[status]}`} />
      </div>
      <p className="mt-0.5 text-xs text-slate-400">{data.subtitle}</p>
      <Handle type="source" position={Position.Right} className="!h-2 !w-2 !bg-slate-300" />
    </div>
  );
}
