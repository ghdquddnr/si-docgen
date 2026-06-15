"use client";

import type { Proposal, ProposalSlide } from "@/lib/api";

const boxed =
  "rounded border border-slate-200 px-2 py-1 focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100";

function newSlide(): ProposalSlide {
  return { title: "신규 섹션", bullets: ["핵심 내용"] };
}

export function ProposalEditor({
  proposal,
  onChange,
}: {
  proposal: Proposal;
  onChange: (next: Proposal) => void;
}) {
  function updateMeta(field: "title" | "client", value: string) {
    onChange({ ...proposal, [field]: value });
  }

  function updateSlide(si: number, field: keyof ProposalSlide, value: unknown) {
    const slides = [...proposal.slides];
    slides[si] = { ...slides[si], [field]: value };
    onChange({ ...proposal, slides });
  }

  function addSlide() {
    onChange({ ...proposal, slides: [...proposal.slides, newSlide()] });
  }

  function deleteSlide(si: number) {
    onChange({ ...proposal, slides: proposal.slides.filter((_, i) => i !== si) });
  }

  return (
    <section className="flex flex-col gap-5">
      <div className="card flex flex-col gap-3 p-4">
        <p className="text-xs font-medium text-slate-500">표지 정보</p>
        <div className="flex flex-wrap gap-4 text-sm">
          <label className="flex flex-1 flex-col gap-1">
            <span className="text-xs text-slate-500">제안서 제목</span>
            <input
              value={proposal.title}
              onChange={(e) => updateMeta("title", e.target.value)}
              className={`font-semibold ${boxed}`}
            />
          </label>
          <label className="flex flex-1 flex-col gap-1">
            <span className="text-xs text-slate-500">발주처</span>
            <input
              value={proposal.client}
              onChange={(e) => updateMeta("client", e.target.value)}
              className={boxed}
            />
          </label>
        </div>
        <p className="text-xs text-slate-400">
          ※ 목차 슬라이드는 다운로드 시 섹션 제목에서 자동 생성됩니다.
        </p>
      </div>

      {proposal.slides.map((slide, si) => (
        <div key={si} className="card flex flex-col gap-3 p-4">
          <div className="flex items-center gap-3">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-indigo-50 text-xs font-semibold text-indigo-700">
              {si + 1}
            </span>
            <input
              value={slide.title}
              onChange={(e) => updateSlide(si, "title", e.target.value)}
              placeholder="섹션 제목"
              className={`flex-1 font-semibold ${boxed}`}
            />
            <button
              onClick={() => deleteSlide(si)}
              disabled={proposal.slides.length <= 1}
              title="슬라이드 삭제"
              className="rounded px-2 py-1 text-xs text-slate-400 hover:bg-red-50 hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-30"
            >
              삭제 ✕
            </button>
          </div>
          <label className="flex flex-col gap-1 text-xs">
            <span className="text-slate-500">핵심 내용 (줄 단위 = 불릿 1개)</span>
            <textarea
              value={slide.bullets.join("\n")}
              onChange={(e) =>
                updateSlide(
                  si,
                  "bullets",
                  e.target.value.split("\n").filter((s) => s.length > 0),
                )
              }
              rows={Math.max(2, slide.bullets.length)}
              className={`${boxed} font-normal`}
            />
          </label>
        </div>
      ))}

      <button
        onClick={addSlide}
        className="w-fit rounded-md border border-dashed border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-500 hover:border-indigo-400 hover:text-indigo-600"
      >
        + 슬라이드 추가
      </button>
    </section>
  );
}
