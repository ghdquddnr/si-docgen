"use client";

import { Background, Controls, ReactFlow, type Edge } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import Link from "next/link";

import PipelineNode, { type PipelineNodeType } from "@/components/canvas/PipelineNode";

const nodeTypes = { pipeline: PipelineNode };

const initialNodes: PipelineNodeType[] = [
  {
    id: "source",
    type: "pipeline",
    position: { x: 0, y: 140 },
    data: { title: "원천 문서", subtitle: "요구사항·RFP 업로드" },
  },
  {
    id: "scenario",
    type: "pipeline",
    position: { x: 300, y: 20 },
    data: { title: "테스트시나리오", subtitle: "LLM 생성", accent: true },
  },
  {
    id: "screen",
    type: "pipeline",
    position: { x: 300, y: 260 },
    data: { title: "화면정의서", subtitle: "LLM 생성", accent: true },
  },
  {
    id: "rtm",
    type: "pipeline",
    position: { x: 620, y: 140 },
    data: { title: "요건추적표(RTM)", subtitle: "REQ→SCR→TC 자동 연결" },
  },
];

const initialEdges: Edge[] = [
  { id: "e-source-scenario", source: "source", target: "scenario", animated: true },
  { id: "e-source-screen", source: "source", target: "screen", animated: true },
  { id: "e-scenario-rtm", source: "scenario", target: "rtm" },
  { id: "e-screen-rtm", source: "screen", target: "rtm" },
];

export default function CanvasPage() {
  return (
    <main className="flex flex-1 flex-col">
      <div className="border-b border-slate-200 bg-white px-6 py-4">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-indigo-600">
              파이프라인 캔버스
            </p>
            <h1 className="text-lg font-bold tracking-tight text-slate-900">산출물 생성 파이프라인</h1>
          </div>
          <Link href="/" className="text-sm text-slate-500 hover:text-slate-900">
            홈으로
          </Link>
        </div>
      </div>

      <div style={{ width: "100%", height: "calc(100vh - 9rem)" }}>
        <ReactFlow
          nodes={initialNodes}
          edges={initialEdges}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.3 }}
        >
          <Background color="#cbd5e1" gap={20} />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
    </main>
  );
}
