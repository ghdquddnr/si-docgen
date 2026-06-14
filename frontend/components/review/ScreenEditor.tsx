"use client";

import type { Screen, ScreenField, ScreenSpec } from "@/lib/api";
import { nextNumberedId } from "@/lib/review";

function newField(existing: ScreenField[]): ScreenField {
  const nextNo = Math.min(20, existing.reduce((m, f) => Math.max(m, f.no), 0) + 1);
  return { no: nextNo, name: "항목", field_type: "텍스트박스", required: false, description: "" };
}

function newScreen(existing: Screen[]): Screen {
  return {
    screen_id: nextNumberedId(
      existing.map((s) => s.screen_id),
      "SCR-",
    ),
    screen_name: "신규 화면",
    menu_path: "홈",
    req_ids: [],
    fields: [newField([])],
    logic: [],
  };
}

const cell =
  "w-full rounded border border-transparent bg-transparent px-1.5 py-1 hover:border-slate-200 focus:border-indigo-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-100";
const boxed =
  "rounded border border-slate-200 px-2 py-1 focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100";

export function ScreenEditor({
  spec,
  onChange,
}: {
  spec: ScreenSpec;
  onChange: (next: ScreenSpec) => void;
}) {
  function updateScreen(si: number, field: keyof Screen, value: unknown) {
    const screens = [...spec.screens];
    screens[si] = { ...screens[si], [field]: value };
    onChange({ ...spec, screens });
  }

  function updateField(si: number, fi: number, field: keyof ScreenField, value: unknown) {
    const fields = [...spec.screens[si].fields];
    fields[fi] = { ...fields[fi], [field]: value };
    updateScreen(si, "fields", fields);
  }

  function addScreen() {
    onChange({ ...spec, screens: [...spec.screens, newScreen(spec.screens)] });
  }

  function deleteScreen(si: number) {
    onChange({ ...spec, screens: spec.screens.filter((_, i) => i !== si) });
  }

  function addField(si: number) {
    const fields = spec.screens[si].fields;
    updateScreen(si, "fields", [...fields, newField(fields)]);
  }

  function deleteField(si: number, fi: number) {
    updateScreen(
      si,
      "fields",
      spec.screens[si].fields.filter((_, i) => i !== fi),
    );
  }

  return (
    <section className="flex flex-col gap-5">
      {spec.screens.map((screen, si) => (
        <div key={si} className="card flex flex-col gap-3 p-4">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
            <input
              value={screen.screen_id}
              onChange={(e) => updateScreen(si, "screen_id", e.target.value)}
              className={`w-28 font-mono ${boxed}`}
            />
            <input
              value={screen.screen_name}
              onChange={(e) => updateScreen(si, "screen_name", e.target.value)}
              placeholder="화면명"
              className={`w-56 font-semibold ${boxed}`}
            />
            <button
              onClick={() => deleteScreen(si)}
              disabled={spec.screens.length <= 1}
              title="화면 삭제"
              className="ml-auto rounded px-2 py-1 text-xs text-slate-400 hover:bg-red-50 hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-30"
            >
              화면 삭제 ✕
            </button>
          </div>

          <div className="flex flex-wrap gap-x-6 gap-y-2 text-xs">
            <label className="flex items-center gap-2">
              <span className="text-slate-500">메뉴 경로</span>
              <input
                value={screen.menu_path}
                onChange={(e) => updateScreen(si, "menu_path", e.target.value)}
                className={`w-72 ${boxed}`}
              />
            </label>
            <label className="flex items-center gap-2">
              <span className="text-slate-500">연관 요건(쉼표)</span>
              <input
                value={screen.req_ids.join(", ")}
                onChange={(e) =>
                  updateScreen(
                    si,
                    "req_ids",
                    e.target.value
                      .split(",")
                      .map((s) => s.trim())
                      .filter((s) => s.length > 0),
                  )
                }
                className={`w-48 ${boxed}`}
              />
            </label>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full border-collapse text-xs">
              <thead className="bg-slate-50 text-left text-slate-500">
                <tr>
                  <th className="border-b border-slate-200 px-2 py-1.5 font-medium">번호</th>
                  <th className="border-b border-slate-200 px-2 py-1.5 font-medium">항목명</th>
                  <th className="border-b border-slate-200 px-2 py-1.5 font-medium">유형</th>
                  <th className="border-b border-slate-200 px-2 py-1.5 font-medium">필수</th>
                  <th className="border-b border-slate-200 px-2 py-1.5 font-medium">설명</th>
                  <th className="border-b border-slate-200 px-2 py-1.5" />
                </tr>
              </thead>
              <tbody>
                {screen.fields.map((f, fi) => (
                  <tr key={fi} className="align-top odd:bg-white even:bg-slate-50/50">
                    <td className="border-b border-slate-100 px-2 py-1">
                      <input
                        type="number"
                        min={1}
                        max={20}
                        value={f.no}
                        onChange={(e) => updateField(si, fi, "no", Number(e.target.value))}
                        className={`w-14 ${cell}`}
                      />
                    </td>
                    <td className="border-b border-slate-100 px-2 py-1">
                      <input
                        value={f.name}
                        onChange={(e) => updateField(si, fi, "name", e.target.value)}
                        className={`w-40 ${cell}`}
                      />
                    </td>
                    <td className="border-b border-slate-100 px-2 py-1">
                      <input
                        value={f.field_type}
                        onChange={(e) => updateField(si, fi, "field_type", e.target.value)}
                        className={`w-28 ${cell}`}
                      />
                    </td>
                    <td className="border-b border-slate-100 px-2 py-1 text-center">
                      <input
                        type="checkbox"
                        checked={f.required}
                        onChange={(e) => updateField(si, fi, "required", e.target.checked)}
                        className="h-4 w-4 accent-indigo-600"
                      />
                    </td>
                    <td className="border-b border-slate-100 px-2 py-1">
                      <input
                        value={f.description}
                        onChange={(e) => updateField(si, fi, "description", e.target.value)}
                        className={`w-56 ${cell}`}
                      />
                    </td>
                    <td className="border-b border-slate-100 px-2 py-1 text-center">
                      <button
                        onClick={() => deleteField(si, fi)}
                        disabled={screen.fields.length <= 1}
                        title="항목 삭제"
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
              onClick={() => addField(si)}
              className="mt-2 w-fit rounded-md border border-dashed border-slate-300 px-3 py-1 text-xs font-medium text-slate-500 hover:border-indigo-400 hover:text-indigo-600"
            >
              + 항목 추가
            </button>
          </div>

          <label className="flex flex-col gap-1 text-xs">
            <span className="text-slate-500">처리 로직 (줄 단위)</span>
            <textarea
              value={screen.logic.join("\n")}
              onChange={(e) =>
                updateScreen(
                  si,
                  "logic",
                  e.target.value.split("\n").filter((s) => s.length > 0),
                )
              }
              rows={Math.max(2, screen.logic.length)}
              className={`${boxed} font-normal`}
            />
          </label>
        </div>
      ))}

      <button
        onClick={addScreen}
        className="w-fit rounded-md border border-dashed border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-500 hover:border-indigo-400 hover:text-indigo-600"
      >
        + 화면 추가
      </button>
    </section>
  );
}
