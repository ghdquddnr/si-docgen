"use client";

import { useRef } from "react";

import type { ManualImageStatus, ManualSection, ManualStep, UserManual } from "@/lib/api";

function newStep(): ManualStep {
  return { instruction: "수행 단계", screen_ref: "", caption: "" };
}

function newSection(): ManualSection {
  return { title: "신규 섹션", description: "", steps: [newStep()] };
}

const cell =
  "w-full rounded border border-transparent bg-transparent px-1.5 py-1 hover:border-slate-200 focus:border-indigo-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-100";
const boxed =
  "rounded border border-slate-200 px-2 py-1 focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100";

// 현재 매뉴얼에서 비어있지 않은 screen_ref 를 순서대로(중복 제거) 모은다.
function distinctRefs(manual: UserManual): string[] {
  const refs: string[] = [];
  for (const s of manual.sections) {
    for (const st of s.steps) {
      if (st.screen_ref && !refs.includes(st.screen_ref)) refs.push(st.screen_ref);
    }
  }
  return refs;
}

export function ManualEditor({
  manual,
  onChange,
  images,
  onUpload,
  onDelete,
  useMockupImages = false,
  onUseMockupImagesChange,
}: {
  manual: UserManual;
  onChange: (next: UserManual) => void;
  images: ManualImageStatus;
  onUpload: (screenRef: string, file: File) => void;
  onDelete: (screenRef: string) => void;
  useMockupImages?: boolean;
  onUseMockupImagesChange?: (val: boolean) => void;
}) {
  function updateSection(si: number, field: keyof ManualSection, value: unknown) {
    const sections = [...manual.sections];
    sections[si] = { ...sections[si], [field]: value };
    onChange({ ...manual, sections });
  }

  function updateStep(si: number, ti: number, field: keyof ManualStep, value: unknown) {
    const steps = [...manual.sections[si].steps];
    steps[ti] = { ...steps[ti], [field]: value };
    updateSection(si, "steps", steps);
  }

  function addSection() {
    onChange({ ...manual, sections: [...manual.sections, newSection()] });
  }

  function deleteSection(si: number) {
    onChange({ ...manual, sections: manual.sections.filter((_, i) => i !== si) });
  }

  function addStep(si: number) {
    updateSection(si, "steps", [...manual.sections[si].steps, newStep()]);
  }

  function deleteStep(si: number, ti: number) {
    updateSection(
      si,
      "steps",
      manual.sections[si].steps.filter((_, i) => i !== ti),
    );
  }

  const refs = distinctRefs(manual);

  return (
    <section className="flex flex-col gap-5">
      {manual.sections.map((section, si) => (
        <div key={si} className="card flex flex-col gap-3 p-4">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
            <span className="text-xs font-semibold text-slate-400">섹션 {si + 1}</span>
            <input
              value={section.title}
              onChange={(e) => updateSection(si, "title", e.target.value)}
              placeholder="섹션 제목"
              className={`w-64 font-semibold ${boxed}`}
            />
            <button
              onClick={() => deleteSection(si)}
              disabled={manual.sections.length <= 1}
              title="섹션 삭제"
              className="ml-auto rounded px-2 py-1 text-xs text-slate-400 hover:bg-red-50 hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-30"
            >
              섹션 삭제 ✕
            </button>
          </div>

          <label className="flex flex-col gap-1 text-xs">
            <span className="text-slate-500">섹션 개요</span>
            <input
              value={section.description}
              onChange={(e) => updateSection(si, "description", e.target.value)}
              className={boxed}
            />
          </label>

          <div className="overflow-x-auto">
            <table className="min-w-full border-collapse text-xs">
              <thead className="bg-slate-50 text-left text-slate-500">
                <tr>
                  <th className="border-b border-slate-200 px-2 py-1.5 font-medium">#</th>
                  <th className="border-b border-slate-200 px-2 py-1.5 font-medium">수행 내용</th>
                  <th className="border-b border-slate-200 px-2 py-1.5 font-medium">화면 참조</th>
                  <th className="border-b border-slate-200 px-2 py-1.5 font-medium">캡션</th>
                  <th className="border-b border-slate-200 px-2 py-1.5" />
                </tr>
              </thead>
              <tbody>
                {section.steps.map((step, ti) => (
                  <tr key={ti} className="align-top odd:bg-white even:bg-slate-50/50">
                    <td className="border-b border-slate-100 px-2 py-1.5 text-slate-400">
                      {ti + 1}
                    </td>
                    <td className="border-b border-slate-100 px-2 py-1.5">
                      <textarea
                        value={step.instruction}
                        onChange={(e) => updateStep(si, ti, "instruction", e.target.value)}
                        rows={2}
                        className="w-80 rounded border border-transparent bg-transparent px-1.5 py-1 hover:border-slate-200 focus:border-indigo-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-100"
                      />
                    </td>
                    <td className="border-b border-slate-100 px-2 py-1.5">
                      <input
                        value={step.screen_ref}
                        onChange={(e) => updateStep(si, ti, "screen_ref", e.target.value)}
                        placeholder="SCR-001"
                        className={`w-28 font-mono ${cell}`}
                      />
                    </td>
                    <td className="border-b border-slate-100 px-2 py-1.5">
                      <input
                        value={step.caption}
                        onChange={(e) => updateStep(si, ti, "caption", e.target.value)}
                        className={`w-44 ${cell}`}
                      />
                    </td>
                    <td className="border-b border-slate-100 px-2 py-1.5 text-center">
                      <button
                        onClick={() => deleteStep(si, ti)}
                        disabled={section.steps.length <= 1}
                        title="단계 삭제"
                        className="rounded px-1.5 py-0.5 text-slate-400 hover:bg-red-50 hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-30"
                      >
                        ✕
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <button
              onClick={() => addStep(si)}
              className="mt-2 w-fit rounded-md border border-dashed border-slate-300 px-3 py-1 text-xs font-medium text-slate-500 hover:border-indigo-400 hover:text-indigo-600"
            >
              + 단계 추가
            </button>
          </div>
        </div>
      ))}

      <button
        onClick={addSection}
        className="w-fit rounded-md border border-dashed border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-500 hover:border-indigo-400 hover:text-indigo-600"
      >
        + 섹션 추가
      </button>

      <div className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white p-3 text-xs">
        <input
          type="checkbox"
          id="use-mockup-images"
          checked={useMockupImages}
          onChange={(e) => onUseMockupImagesChange?.(e.target.checked)}
          className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
        />
        <label htmlFor="use-mockup-images" className="font-semibold text-slate-700 cursor-pointer">
          화면 설계서 목업 이미지 사용
        </label>
        <span className="text-slate-400">
          (미업로드된 화면 자리에 화면정의서의 목업 영역을 고해상도 PNG로 자동 추출하여 삽입합니다)
        </span>
      </div>

      <ImagePanel refs={refs} images={images} onUpload={onUpload} onDelete={onDelete} />
    </section>
  );
}

function ImagePanel({
  refs,
  images,
  onUpload,
  onDelete,
}: {
  refs: string[];
  images: ManualImageStatus;
  onUpload: (screenRef: string, file: File) => void;
  onDelete: (screenRef: string) => void;
}) {
  return (
    <div className="card flex flex-col gap-3 p-4">
      <div>
        <h3 className="text-sm font-semibold text-slate-700">화면 캡처</h3>
        <p className="mt-0.5 text-xs text-slate-500">
          단계의 화면 참조(screen_ref)별로 캡처 이미지를 업로드하면 매뉴얼에 삽입됩니다. 업로드하지
          않은 참조는 플레이스홀더로 표시됩니다. 새 화면 참조는 먼저 저장(재검증) 후 업로드하세요.
        </p>
      </div>
      {refs.length === 0 ? (
        <p className="text-xs text-slate-400">화면 참조가 있는 단계가 없습니다.</p>
      ) : (
        <ul className="flex flex-col divide-y divide-slate-100">
          {refs.map((ref) => (
            <ImageRow
              key={ref}
              screenRef={ref}
              uploaded={images[ref] ?? false}
              onUpload={onUpload}
              onDelete={onDelete}
            />
          ))}
        </ul>
      )}
    </div>
  );
}

function ImageRow({
  screenRef,
  uploaded,
  onUpload,
  onDelete,
}: {
  screenRef: string;
  uploaded: boolean;
  onUpload: (screenRef: string, file: File) => void;
  onDelete: (screenRef: string) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  return (
    <li className="flex items-center gap-3 py-2 text-xs">
      <span className="w-28 font-mono text-slate-700">{screenRef}</span>
      <span
        className={`rounded-full px-2 py-0.5 ${
          uploaded ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-500"
        }`}
      >
        {uploaded ? "업로드됨" : "미업로드"}
      </span>
      <input
        ref={inputRef}
        type="file"
        accept=".png,.jpg,.jpeg,.gif,.bmp"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) onUpload(screenRef, f);
          e.target.value = "";
        }}
        className="hidden"
      />
      <button
        onClick={() => inputRef.current?.click()}
        className="ml-auto rounded-md border border-slate-300 px-2.5 py-1 font-medium text-slate-600 hover:border-indigo-400 hover:text-indigo-600"
      >
        {uploaded ? "교체" : "업로드"}
      </button>
      {uploaded && (
        <button
          onClick={() => onDelete(screenRef)}
          className="rounded-md px-2 py-1 text-slate-400 hover:bg-red-50 hover:text-red-600"
        >
          삭제
        </button>
      )}
    </li>
  );
}
