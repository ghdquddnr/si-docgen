"use client";

import {
  Background,
  Controls,
  Panel,
  ReactFlow,
  useNodesState,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import {
  ApiError,
  createJob,
  eventsUrl,
  renderJob,
  type CoverInfo,
  type ProgressEvent,
} from "@/lib/api";
import { LlmNode, OutputNode, SourceNode, type NodeStatus } from "@/components/canvas/nodes";

const nodeTypes = { source: SourceNode, llm: LlmNode, output: OutputNode };

const POSITIONS: Record<string, { x: number; y: number }> = {
  source: { x: 0, y: 150 },
  scenario: { x: 300, y: 0 },
  screen: { x: 300, y: 240 },
  rtm: { x: 640, y: 150 },
};

const edges: Edge[] = [
  { id: "e-source-scenario", source: "source", target: "scenario", animated: true },
  { id: "e-source-screen", source: "source", target: "screen", animated: true },
  { id: "e-scenario-rtm", source: "scenario", target: "rtm" },
  { id: "e-screen-rtm", source: "screen", target: "rtm" },
];

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

function nodeStatuses(running: boolean, ev: ProgressEvent | null) {
  const prog = ev?.progress ?? null;
  const term = ev?.status;
  const ok = term === "succeeded";
  const fail = term === "failed";
  const inScenario = prog === null || prog === "queued" || prog === "scenario";
  const inScreens = prog === "screens";
  const scenario: NodeStatus = ok
    ? "done"
    : fail
      ? inScenario
        ? "error"
        : "done"
      : running
        ? inScenario
          ? "running"
          : "done"
        : "idle";
  const screen: NodeStatus = ok
    ? "done"
    : fail
      ? inScreens
        ? "error"
        : "idle"
      : running && inScreens
        ? "running"
        : "idle";
  const output: NodeStatus = ok ? "done" : fail ? "error" : "idle";
  return { scenario, screen, output };
}

export default function CanvasPage() {
  const [file, setFile] = useState<File | null>(null);
  const [models, setModels] = useState({ scenario: "", screen: "" });
  const [cover, setCover] = useState<CoverInfo>({
    project_name: "",
    system_name: "",
    author: "",
    written_date: today(),
  });
  const [jobId, setJobId] = useState<string | null>(null);
  const [event, setEvent] = useState<ProgressEvent | null>(null);
  const [running, setRunning] = useState(false);
  const [downloads, setDownloads] = useState<Record<string, string> | null>(null);
  const [rendering, setRendering] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sourceRef = useRef<EventSource | null>(null);

  useEffect(() => () => sourceRef.current?.close(), []);

  const doRender = useCallback(async () => {
    if (!jobId) return;
    setRendering(true);
    try {
      const r = await renderJob(jobId);
      setDownloads(r.downloads);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "렌더링 실패");
    } finally {
      setRendering(false);
    }
  }, [jobId]);

  const st = nodeStatuses(running, event);

  // 노드 data 를 앱 상태에서 파생한다 (측정/엣지는 useNodesState 가 관리)
  const buildData = useCallback(
    (id: string): Record<string, unknown> => {
      switch (id) {
        case "source":
          return { filename: file?.name ?? null, onPick: setFile, status: file ? "done" : "idle", disabled: running };
        case "scenario":
          return {
            title: "테스트시나리오",
            status: st.scenario,
            model: models.scenario,
            onModel: (m: string) => setModels((s) => ({ ...s, scenario: m })),
            disabled: running,
          };
        case "screen":
          return {
            title: "화면정의서",
            status: st.screen,
            model: models.screen,
            onModel: (m: string) => setModels((s) => ({ ...s, screen: m })),
            disabled: running,
          };
        default:
          return { status: st.output, jobId, downloads, onRender: doRender, rendering };
      }
    },
    [file, running, st.scenario, st.screen, st.output, models, jobId, downloads, rendering, doRender],
  );

  const [rfNodes, setRfNodes, onNodesChange] = useNodesState<Node>(
    ["source", "scenario", "screen", "rtm"].map((id) => ({
      id,
      type: id === "source" ? "source" : id === "rtm" ? "output" : "llm",
      position: POSITIONS[id],
      data: buildData(id),
    })),
  );

  useEffect(() => {
    setRfNodes((nds) => nds.map((n) => ({ ...n, data: buildData(n.id) })));
  }, [buildData, setRfNodes]);

  async function run() {
    if (!file) {
      setError("원천 문서를 선택하세요.");
      return;
    }
    setError(null);
    setDownloads(null);
    setEvent(null);
    try {
      const job = await createJob(file, cover, {
        withScreens: true,
        scenarioModel: models.scenario,
        screenSpecModel: models.screen,
      });
      setJobId(job.id);
      setRunning(true);
      sourceRef.current?.close();
      const src = new EventSource(eventsUrl(job.id));
      sourceRef.current = src;
      src.addEventListener("progress", (e) => {
        const d = JSON.parse((e as MessageEvent).data) as ProgressEvent;
        setEvent(d);
        if (d.terminal) {
          setRunning(false);
          src.close();
        }
      });
      src.addEventListener("error", () => src.close());
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "실행에 실패했습니다.");
    }
  }

  return (
    <main className="flex flex-1 flex-col">
      <div className="border-b border-slate-200 bg-white px-6 py-4">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-indigo-600">
              파이프라인 캔버스
            </p>
            <h1 className="text-lg font-bold tracking-tight text-slate-900">
              산출물 생성 파이프라인
            </h1>
          </div>
          <Link href="/" className="text-sm text-slate-500 hover:text-slate-900">
            홈으로
          </Link>
        </div>
      </div>

      <div style={{ width: "100%", height: "calc(100vh - 9rem)" }}>
        <ReactFlow
          nodes={rfNodes}
          edges={edges}
          nodeTypes={nodeTypes}
          onNodesChange={onNodesChange}
          nodesDraggable={false}
          nodesConnectable={false}
          fitView
          fitViewOptions={{ padding: 0.25 }}
        >
          <Background color="#cbd5e1" gap={20} />
          <Controls showInteractive={false} />

          <Panel position="top-left" className="!m-3">
            <div className="flex w-64 flex-col gap-2 rounded-xl border border-slate-200 bg-white/95 p-3 shadow-sm backdrop-blur">
              <p className="text-xs font-semibold text-slate-600">표지 정보</p>
              {(["project_name", "system_name", "author"] as const).map((k) => (
                <input
                  key={k}
                  placeholder={
                    { project_name: "프로젝트명", system_name: "시스템명", author: "작성자" }[k]
                  }
                  value={cover[k]}
                  disabled={running}
                  onChange={(e) => setCover({ ...cover, [k]: e.target.value })}
                  className="rounded-md border border-slate-300 px-2 py-1 text-xs focus:border-indigo-400 focus:outline-none"
                />
              ))}
              <button
                onClick={run}
                disabled={running || !file}
                className="mt-1 rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                {running ? "실행 중…" : "▶ 실행"}
              </button>
              {error && <p className="text-xs text-red-600">{error}</p>}
              {event?.status === "failed" && (
                <p className="text-xs text-red-600">실패: {event.error}</p>
              )}
            </div>
          </Panel>
        </ReactFlow>
      </div>
    </main>
  );
}
