"use client";

import { useCallback, useEffect, useState } from "react";

import { Icon } from "@/components/Icon";
import {
  ApiError,
  createTemplateFolder,
  defaultTemplateUrl,
  deleteTemplate,
  deleteTemplateFolder,
  getTemplateLibrary,
  uploadTemplate,
  type Template,
  type TemplateFolder,
  type TemplateLibrary,
} from "@/lib/api";

export default function TemplatesPage() {
  const [lib, setLib] = useState<TemplateLibrary | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLib(await getTemplateLibrary());
  }, []);

  useEffect(() => {
    getTemplateLibrary()
      .then(setLib)
      .catch(() => setErr("양식 보관함을 불러오지 못했습니다."));
  }, []);

  function flash(message: string) {
    setMsg(message);
    setErr(null);
  }
  function fail(e: unknown, fallback: string) {
    setErr(e instanceof ApiError ? e.message : fallback);
    setMsg(null);
  }

  async function handleDeleteFolder(id: string) {
    if (!confirm("폴더와 그 안의 모든 양식을 삭제할까요?")) return;
    try {
      await deleteTemplateFolder(id);
      await refresh();
      flash("폴더를 삭제했습니다.");
    } catch (e) {
      fail(e, "폴더 삭제에 실패했습니다.");
    }
  }

  async function handleDeleteTemplate(id: string) {
    if (!confirm("이 양식을 삭제할까요?")) return;
    try {
      await deleteTemplate(id);
      await refresh();
      flash("양식을 삭제했습니다.");
    } catch (e) {
      fail(e, "양식 삭제에 실패했습니다.");
    }
  }

  if (!lib) {
    return (
      <div className="mx-auto w-full max-w-4xl px-6 py-8">
        <p className="text-sm text-slate-400">불러오는 중…</p>
        {err && <p className="mt-2 text-sm text-red-600">{err}</p>}
      </div>
    );
  }

  const rootFolders = lib.folders.filter((f) => f.parent_id === null);
  const rootTemplates = lib.templates.filter((t) => t.folder_id === null);

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 px-6 py-8">
      <div className="space-y-1">
        <h2 className="text-2xl font-bold tracking-tight text-slate-900">양식 보관함</h2>
        <p className="text-sm text-slate-500">
          회사·고객사별 양식을 폴더로 보관하고, 문서 생성 시 선택할 수 있습니다. 기본 양식을 내려받아
          로고·서식만 바꾼 뒤 업로드하세요(구조는 유지해야 합니다).
        </p>
      </div>

      {(msg || err) && (
        <div
          className={`rounded-lg px-3 py-2 text-sm ${
            err ? "bg-red-50 text-red-700" : "bg-emerald-50 text-emerald-700"
          }`}
        >
          {err ?? msg}
        </div>
      )}

      <UploadPanel lib={lib} onDone={refresh} onFlash={flash} onFail={fail} />
      <NewFolderPanel lib={lib} onDone={refresh} onFail={fail} />
      <DefaultDownloads lib={lib} />

      <section>
        <h3 className="mb-3 text-sm font-semibold text-slate-500">보관된 양식</h3>
        {rootFolders.length === 0 && rootTemplates.length === 0 ? (
          <div className="card p-5 text-center text-sm text-slate-400">
            아직 보관된 양식이 없습니다. 위에서 폴더를 만들거나 양식을 업로드하세요.
          </div>
        ) : (
          <div className="card flex flex-col gap-1 p-3">
            {rootFolders.map((f) => (
              <FolderNode
                key={f.id}
                folder={f}
                lib={lib}
                depth={0}
                onDeleteFolder={handleDeleteFolder}
                onDeleteTemplate={handleDeleteTemplate}
              />
            ))}
            {rootTemplates.map((t) => (
              <TemplateRow
                key={t.id}
                tpl={t}
                lib={lib}
                depth={0}
                onDelete={handleDeleteTemplate}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function kindLabel(lib: TemplateLibrary, kind: string): string {
  return lib.kinds.find((k) => k.kind === kind)?.label ?? kind;
}

function FolderNode({
  folder,
  lib,
  depth,
  onDeleteFolder,
  onDeleteTemplate,
}: {
  folder: TemplateFolder;
  lib: TemplateLibrary;
  depth: number;
  onDeleteFolder: (id: string) => void;
  onDeleteTemplate: (id: string) => void;
}) {
  const subFolders = lib.folders.filter((f) => f.parent_id === folder.id);
  const templates = lib.templates.filter((t) => t.folder_id === folder.id);
  return (
    <div>
      <div
        className="group flex items-center gap-2 rounded-md px-2 py-1.5 hover:bg-slate-50"
        style={{ paddingLeft: `${depth * 18 + 8}px` }}
      >
        <Icon name="dashboard" className="h-4 w-4 text-amber-500" />
        <span className="text-sm font-medium text-slate-700">{folder.name}</span>
        <span className="text-xs text-slate-400">
          {subFolders.length + templates.length}개
        </span>
        <button
          onClick={() => onDeleteFolder(folder.id)}
          className="ml-auto rounded px-1.5 py-0.5 text-xs text-slate-400 opacity-0 hover:bg-red-50 hover:text-red-600 group-hover:opacity-100"
        >
          삭제
        </button>
      </div>
      {subFolders.map((f) => (
        <FolderNode
          key={f.id}
          folder={f}
          lib={lib}
          depth={depth + 1}
          onDeleteFolder={onDeleteFolder}
          onDeleteTemplate={onDeleteTemplate}
        />
      ))}
      {templates.map((t) => (
        <TemplateRow key={t.id} tpl={t} lib={lib} depth={depth + 1} onDelete={onDeleteTemplate} />
      ))}
    </div>
  );
}

function TemplateRow({
  tpl,
  lib,
  depth,
  onDelete,
}: {
  tpl: Template;
  lib: TemplateLibrary;
  depth: number;
  onDelete: (id: string) => void;
}) {
  return (
    <div
      className="group flex items-center gap-2 rounded-md px-2 py-1.5 hover:bg-slate-50"
      style={{ paddingLeft: `${depth * 18 + 8}px` }}
    >
      <Icon name="requirement" className="h-4 w-4 text-slate-400" />
      <span className="text-sm text-slate-700">{tpl.name}</span>
      <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-500">
        {kindLabel(lib, tpl.kind)}
      </span>
      <button
        onClick={() => onDelete(tpl.id)}
        className="ml-auto rounded px-1.5 py-0.5 text-xs text-slate-400 opacity-0 hover:bg-red-50 hover:text-red-600 group-hover:opacity-100"
      >
        삭제
      </button>
    </div>
  );
}

function UploadPanel({
  lib,
  onDone,
  onFlash,
  onFail,
}: {
  lib: TemplateLibrary;
  onDone: () => Promise<void>;
  onFlash: (m: string) => void;
  onFail: (e: unknown, fallback: string) => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [kind, setKind] = useState(lib.kinds[0]?.kind ?? "");
  const [name, setName] = useState("");
  const [folderId, setFolderId] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) {
      onFail(null, "양식 파일을 선택하세요.");
      return;
    }
    setBusy(true);
    try {
      await uploadTemplate(file, kind, name, folderId || null);
      setFile(null);
      setName("");
      await onDone();
      onFlash("양식을 업로드했습니다.");
    } catch (e) {
      onFail(e, "업로드에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }

  const ext = lib.kinds.find((k) => k.kind === kind)?.ext ?? "";

  return (
    <form onSubmit={submit} className="card flex flex-col gap-4 p-5">
      <p className="text-sm font-semibold text-slate-700">양식 업로드</p>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="field-label">산출물 종류</label>
          <select value={kind} onChange={(e) => setKind(e.target.value)} className="field-input">
            {lib.kinds.map((k) => (
              <option key={k.kind} value={k.kind}>
                {k.label} ({k.ext})
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="field-label">폴더 (선택)</label>
          <select
            value={folderId}
            onChange={(e) => setFolderId(e.target.value)}
            className="field-input"
          >
            <option value="">최상위</option>
            {lib.folders.map((f) => (
              <option key={f.id} value={f.id}>
                {f.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="field-label">이름 (선택)</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="예: A사 표준 양식"
            className="field-input"
          />
        </div>
        <div>
          <label className="field-label">파일 ({ext})</label>
          <input
            type="file"
            accept={ext}
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="field-input"
          />
        </div>
      </div>
      <button type="submit" disabled={busy} className="btn-primary self-start">
        {busy ? "업로드 중…" : "업로드"}
      </button>
    </form>
  );
}

function NewFolderPanel({
  lib,
  onDone,
  onFail,
}: {
  lib: TemplateLibrary;
  onDone: () => Promise<void>;
  onFail: (e: unknown, fallback: string) => void;
}) {
  const [name, setName] = useState("");
  const [parentId, setParentId] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setBusy(true);
    try {
      await createTemplateFolder(name.trim(), parentId || null);
      setName("");
      await onDone();
    } catch (e) {
      onFail(e, "폴더 생성에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="card flex flex-wrap items-end gap-3 p-5">
      <div className="flex-1">
        <label className="field-label">새 폴더</label>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="예: 고객사A / 우리회사 표준"
          className="field-input"
        />
      </div>
      <div>
        <label className="field-label">상위 폴더</label>
        <select
          value={parentId}
          onChange={(e) => setParentId(e.target.value)}
          className="field-input"
        >
          <option value="">최상위</option>
          {lib.folders.map((f) => (
            <option key={f.id} value={f.id}>
              {f.name}
            </option>
          ))}
        </select>
      </div>
      <button type="submit" disabled={busy} className="btn-secondary">
        폴더 만들기
      </button>
    </form>
  );
}

function DefaultDownloads({ lib }: { lib: TemplateLibrary }) {
  return (
    <section>
      <h3 className="mb-2 text-sm font-semibold text-slate-500">기본 양식 내려받기</h3>
      <p className="mb-3 text-xs text-slate-400">
        기본 양식을 받아 서식만 수정한 뒤 위에서 업로드하면 해당 양식으로 생성됩니다.
      </p>
      <div className="flex flex-wrap gap-2">
        {lib.kinds.map((k) => (
          <a
            key={k.kind}
            href={defaultTemplateUrl(k.kind)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 px-3 py-1.5 text-xs text-slate-600 hover:border-indigo-400 hover:text-indigo-600"
          >
            <Icon name="manual" className="h-4 w-4" />
            {k.label}
          </a>
        ))}
      </div>
    </section>
  );
}
