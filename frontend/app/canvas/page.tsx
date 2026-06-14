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
  source: { x: 0, y: 220 },
  requirement: { x: 280, y: 120 },
  scenario: { x: 560, y: -20 },
  screen: { x: 560, y: 200 },
  wbs: { x: 280, y: 360 },
  tableSpec: { x: 280, y: 500 },
  rtm: { x: 840, y: 120 },
};

const edges: Edge[] = [
  { id: "e-source-req", source: "source", target: "requirement", animated: true },
  { id: "e-source-wbs", source: "source", target: "wbs", animated: true },
  { id: "e-source-tablespec", source: "source", target: "tableSpec", animated: true },
  { id: "e-req-scenario", source: "requirement", target: "scenario", animated: true },
  { id: "e-req-screen", source: "requirement", target: "screen", animated: true },
  { id: "e-scenario-rtm", source: "scenario", target: "rtm" },
  { id: "e-screen-rtm", source: "screen", target: "rtm" },
];

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

// 진행 단계 순서(노드 보유 단계). progress 값이 이 중 어디인지로 노드 상태를 파생한다.
const STAGES = ["requirements", "scenario", "screens", "wbs", "table_spec"] as const;

function nodeStatuses(running: boolean, ev: ProgressEvent | null) {
  const prog = ev?.progress ?? null;
  const term = ev?.status;
  const ok = term === "succeeded";
  const fail = term === "failed";
  // queued/null 은 첫 단계(요구사항) 직전 → 인덱스 0 으로 본다
  const curIdx = prog ? STAGES.indexOf(prog as (typeof STAGES)[number]) : -1;
  const activeIdx = curIdx < 0 ? 0 : curIdx;

  const statusFor = (idx: number): NodeStatus => {
    if (ok) return "done";
    if (fail) return idx < activeIdx ? "done" : idx === activeIdx ? "error" : "idle";
    if (running) return idx < activeIdx ? "done" : idx === activeIdx ? "running" : "idle";
    return "idle";
  };

  return {
    requirement: statusFor(0),
    scenario: statusFor(1),
    screen: statusFor(2),
    wbs: statusFor(3),
    tableSpec: statusFor(4),
    output: ok ? "done" : fail ? "error" : "idle",
  };
}

export default function CanvasPage() {
  const [file, setFile] = useState<File | null>(null);
  const [models, setModels] = useState({
    requirement: "",
    scenario: "",
    screen: "",
    wbs: "",
    tableSpec: "",
  });
  const [startDate, setStartDate] = useState(today());
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
        case "requirement":
          return {
            title: "요구사항정의서",
            status: st.requirement,
            model: models.requirement,
            onModel: (m: string) => setModels((s) => ({ ...s, requirement: m })),
            disabled: running,
          };
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
        case "wbs":
          return {
            title: "WBS",
            status: st.wbs,
            model: models.wbs,
            onModel: (m: string) => setModels((s) => ({ ...s, wbs: m })),
            disabled: running,
          };
        case "tableSpec":
          return {
            title: "테이블정의서",
            status: st.tableSpec,
            model: models.tableSpec,
            onModel: (m: string) => setModels((s) => ({ ...s, tableSpec: m })),
            disabled: running,
          };
        default:
          return { status: st.output, jobId, downloads, onRender: doRender, rendering };
      }
    },
    [file, running, st.requirement, st.scenario, st.screen, st.wbs, st.tableSpec, st.output, models, jobId, downloads, rendering, doRender],
  );

  const [rfNodes, setRfNodes, onNodesChange] = useNodesState<Node>(
    ["source", "requirement", "scenario", "screen", "wbs", "tableSpec", "rtm"].map((id) => ({
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
        withRequirements: true,
        withWbs: true,
        withTableSpec: true,
        startDate,
        requirementSpecModel: models.requirement,
        scenarioModel: models.scenario,
        screenSpecModel: models.screen,
        wbsModel: models.wbs,
        tableSpecModel: models.tableSpec,
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
        <div className="mx-auto max-w-6xl">
          <p className="text-xs font-semibold uppercase tracking-wider text-indigo-600">
            파이프라인 캔버스
          </p>
          <h1 className="text-lg font-bold tracking-tight text-slate-900">
            산출물 생성 파이프라인
          </h1>
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
              <label className="flex items-center justify-between gap-2 text-xs text-slate-500">
                WBS 시작일
                <input
                  type="date"
                  value={startDate}
                  disabled={running}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="rounded-md border border-slate-300 px-2 py-1 text-xs focus:border-indigo-400 focus:outline-none"
                />
              </label>
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
