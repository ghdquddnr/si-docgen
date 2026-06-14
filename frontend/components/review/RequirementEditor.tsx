"use client";

import type { Priority, Requirement, RequirementSpec } from "@/lib/api";
import { nextNumberedId } from "@/lib/review";

const PRIORITIES: Priority[] = ["상", "중", "하"];
const CATEGORY_OPTIONS = ["기능", "비기능", "인터페이스", "보안"];

function newRequirement(existing: Requirement[]): Requirement {
  return {
    req_id: nextNumberedId(
      existing.map((r) => r.req_id),
      "REQ-",
    ),
    name: "신규 요건",
    category: "기능",
    priority: "중",
    description: "요건 상세 설명",
    note: "",
  };
}

const cell =
  "w-full rounded border border-transparent bg-transparent px-1.5 py-1 hover:border-slate-200 focus:border-indigo-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-100";

export function RequirementEditor({
  spec,
  onChange,
}: {
  spec: RequirementSpec;
  onChange: (next: RequirementSpec) => void;
}) {
  function updateReq(index: number, field: keyof Requirement, value: unknown) {
    const requirements = [...spec.requirements];
    requirements[index] = { ...requirements[index], [field]: value };
    onChange({ ...spec, requirements });
  }

  function addReq() {
    onChange({ ...spec, requirements: [...spec.requirements, newRequirement(spec.requirements)] });
  }

  function deleteReq(index: number) {
    onChange({ ...spec, requirements: spec.requirements.filter((_, i) => i !== index) });
  }

  return (
    <section className="flex flex-col gap-4">
      <div className="card flex flex-wrap items-center gap-x-6 gap-y-2 p-4 text-sm">
        <label className="flex items-center gap-2">
          <span className="text-slate-500">문서번호</span>
          <input
            value={spec.doc_no}
            onChange={(e) => onChange({ ...spec, doc_no: e.target.value })}
            className="w-48 rounded border border-slate-200 px-2 py-1 focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
          />
        </label>
        <span className="text-slate-400">요건 {spec.requirements.length}건</span>
      </div>

      <div className="card overflow-x-auto">
        <datalist id="category-options">
          {CATEGORY_OPTIONS.map((c) => (
            <option key={c} value={c} />
          ))}
        </datalist>
        <table className="min-w-full border-collapse text-xs">
          <thead className="bg-slate-50 text-left text-slate-500">
            <tr>
              <th className="border-b border-slate-200 px-3 py-2 font-medium">요건 ID</th>
              <th className="border-b border-slate-200 px-3 py-2 font-medium">요건명</th>
              <th className="border-b border-slate-200 px-3 py-2 font-medium">구분</th>
              <th className="border-b border-slate-200 px-3 py-2 font-medium">중요도</th>
              <th className="border-b border-slate-200 px-3 py-2 font-medium">상세 설명</th>
              <th className="border-b border-slate-200 px-3 py-2 font-medium">비고</th>
              <th className="border-b border-slate-200 px-2 py-2" />
            </tr>
          </thead>
          <tbody>
            {spec.requirements.map((req, i) => (
              <tr key={i} className="align-top odd:bg-white even:bg-slate-50/50">
                <td className="border-b border-slate-100 px-2 py-1.5">
                  <input
                    value={req.req_id}
                    onChange={(e) => updateReq(i, "req_id", e.target.value)}
                    className={`w-24 ${cell}`}
                  />
                </td>
                <td className="border-b border-slate-100 px-2 py-1.5">
                  <input
                    value={req.name}
                    onChange={(e) => updateReq(i, "name", e.target.value)}
                    className={`w-48 ${cell}`}
                  />
                </td>
                <td className="border-b border-slate-100 px-2 py-1.5">
                  <input
                    list="category-options"
                    value={req.category}
                    onChange={(e) => updateReq(i, "category", e.target.value)}
                    className={`w-24 ${cell}`}
                  />
                </td>
                <td className="border-b border-slate-100 px-2 py-1.5">
                  <select
                    value={req.priority}
                    onChange={(e) => updateReq(i, "priority", e.target.value as Priority)}
                    className={`w-16 ${cell}`}
                  >
                    {PRIORITIES.map((p) => (
                      <option key={p} value={p}>
                        {p}
                      </option>
                    ))}
                  </select>
                </td>
                <td className="border-b border-slate-100 px-2 py-1.5">
                  <textarea
                    value={req.description}
                    onChange={(e) => updateReq(i, "description", e.target.value)}
                    rows={2}
                    className={`w-80 ${cell}`}
                  />
                </td>
                <td className="border-b border-slate-100 px-2 py-1.5">
                  <input
                    value={req.note}
                    onChange={(e) => updateReq(i, "note", e.target.value)}
                    className={`w-32 ${cell}`}
                  />
                </td>
                <td className="border-b border-slate-100 px-2 py-1.5 text-center">
                  <button
                    onClick={() => deleteReq(i)}
                    disabled={spec.requirements.length <= 1}
                    title="요건 삭제"
                    className="rounded px-1.5 py-0.5 text-slate-400 hover:bg-red-50 hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-30"
                  >
                    ✕
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <button
        onClick={addReq}
        className="w-fit rounded-md border border-dashed border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-500 hover:border-indigo-400 hover:text-indigo-600"
      >
        + 요건 추가
      </button>
    </section>
  );
}
