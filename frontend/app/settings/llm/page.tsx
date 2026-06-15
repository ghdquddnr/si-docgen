"use client";

import { useEffect, useState } from "react";

import {
  ApiError,
  createLlmCredential,
  createLlmModel,
  deleteLlmCredential,
  deleteLlmModel,
  getEncryptionStatus,
  listLlmCredentials,
  listLlmModels,
  listLlmProviders,
  listOllamaTags,
  setLlmModelEnabled,
  type LlmCredential,
  type LlmModelEntry,
  type LlmProvider,
} from "@/lib/api";

export default function LlmSettingsPage() {
  const [providers, setProviders] = useState<LlmProvider[]>([]);
  const [credentials, setCredentials] = useState<LlmCredential[]>([]);
  const [models, setModels] = useState<LlmModelEntry[]>([]);
  const [encryptionOk, setEncryptionOk] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    const [creds, mods] = await Promise.all([listLlmCredentials(), listLlmModels(false)]);
    setCredentials(creds);
    setModels(mods);
  }

  useEffect(() => {
    listLlmProviders().then(setProviders).catch(() => setProviders([]));
    getEncryptionStatus()
      .then((s) => setEncryptionOk(s.configured))
      .catch(() => setEncryptionOk(true));
    listLlmCredentials().then(setCredentials).catch(() => setCredentials([]));
    listLlmModels(false).then(setModels).catch(() => setModels([]));
  }, []);

  const keyProviders = providers.filter((p) => p.needs_key);
  const providerLabel = (id: string) => providers.find((p) => p.provider === id)?.label ?? id;

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 px-6 py-8">
      <div className="space-y-1">
        <h2 className="text-2xl font-bold tracking-tight text-slate-900">LLM 설정</h2>
        <p className="text-sm text-slate-500">
          로컬(Ollama)·상용(OpenAI·Gemini·Anthropic·Grok) 모델을 등록하면 각 문서 생성 화면의
          “생성 모델” 목록에 나타납니다. 상용 API 키는 암호화되어 저장됩니다.
        </p>
      </div>

      {!encryptionOk && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          API 키 암호화 마스터 키(<code>SIDOCGEN_SECRET_KEY</code>)가 설정되지 않았습니다. 상용 키
          저장 전에 <code>.env</code> 에 임의의 비밀 문자열로 설정하세요. (Ollama 모델은 키 없이
          등록 가능합니다.)
        </div>
      )}

      {error && (
        <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
      )}

      <ApiKeySection
        keyProviders={keyProviders}
        credentials={credentials}
        providerLabel={providerLabel}
        onChange={refresh}
        onError={setError}
      />

      <ModelSection
        providers={providers}
        credentials={credentials}
        models={models}
        providerLabel={providerLabel}
        onChange={refresh}
        onError={setError}
      />
    </div>
  );
}

function ApiKeySection({
  keyProviders,
  credentials,
  providerLabel,
  onChange,
  onError,
}: {
  keyProviders: LlmProvider[];
  credentials: LlmCredential[];
  providerLabel: (id: string) => string;
  onChange: () => Promise<void>;
  onError: (m: string | null) => void;
}) {
  const [provider, setProvider] = useState("");
  const [label, setLabel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [busy, setBusy] = useState(false);

  async function add() {
    onError(null);
    if (!provider || !apiKey.trim()) {
      onError("제공자와 API 키를 입력하세요.");
      return;
    }
    setBusy(true);
    try {
      await createLlmCredential(provider, apiKey.trim(), label.trim());
      setApiKey("");
      setLabel("");
      await onChange();
    } catch (e) {
      onError(e instanceof ApiError ? e.message : "키 저장에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    onError(null);
    try {
      await deleteLlmCredential(id);
      await onChange();
    } catch (e) {
      onError(e instanceof ApiError ? e.message : "삭제에 실패했습니다.");
    }
  }

  return (
    <section className="card flex flex-col gap-4 p-5">
      <h3 className="text-sm font-semibold text-slate-700">API 키</h3>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-[1fr_1fr_2fr_auto]">
        <select
          value={provider}
          onChange={(e) => setProvider(e.target.value)}
          className="field-input"
        >
          <option value="">제공자 선택</option>
          {keyProviders.map((p) => (
            <option key={p.provider} value={p.provider}>
              {p.label}
            </option>
          ))}
        </select>
        <input
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          placeholder="이름 (선택)"
          className="field-input"
        />
        <input
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder="API 키"
          type="password"
          className="field-input"
        />
        <button onClick={add} disabled={busy} className="btn-primary whitespace-nowrap">
          저장
        </button>
      </div>

      {credentials.length === 0 ? (
        <p className="text-sm text-slate-400">저장된 키가 없습니다.</p>
      ) : (
        <ul className="divide-y divide-slate-100">
          {credentials.map((c) => (
            <li key={c.id} className="flex items-center justify-between py-2 text-sm">
              <div className="flex items-center gap-3">
                <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                  {providerLabel(c.provider)}
                </span>
                <span className="font-medium text-slate-700">{c.label}</span>
                <span className="font-mono text-xs text-slate-400">{c.key_preview}</span>
              </div>
              <button
                onClick={() => remove(c.id)}
                className="rounded px-2 py-1 text-xs text-slate-400 hover:bg-red-50 hover:text-red-600"
              >
                삭제
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function ModelSection({
  providers,
  credentials,
  models,
  providerLabel,
  onChange,
  onError,
}: {
  providers: LlmProvider[];
  credentials: LlmCredential[];
  models: LlmModelEntry[];
  providerLabel: (id: string) => string;
  onChange: () => Promise<void>;
  onError: (m: string | null) => void;
}) {
  const [provider, setProvider] = useState("");
  const [label, setLabel] = useState("");
  const [name, setName] = useState("");
  const [credentialId, setCredentialId] = useState("");
  const [busy, setBusy] = useState(false);
  const [tags, setTags] = useState<string[]>([]);

  const needsKey = providers.find((p) => p.provider === provider)?.needs_key ?? false;
  const credsForProvider = credentials.filter((c) => c.provider === provider);

  async function loadTags() {
    onError(null);
    const t = await listOllamaTags();
    setTags(t);
    if (t.length === 0) onError("실행 중인 Ollama 에서 모델을 찾지 못했습니다 (서버·모델 확인).");
  }

  async function add() {
    onError(null);
    if (!provider || !name.trim()) {
      onError("제공자와 모델명을 입력하세요.");
      return;
    }
    // 모델 식별자에 provider 접두사가 없으면 자동으로 붙인다 (예: gpt-4o → openai/gpt-4o)
    const model = name.includes("/") ? name.trim() : `${provider}/${name.trim()}`;
    setBusy(true);
    try {
      await createLlmModel({
        label: label.trim(),
        provider,
        model,
        credential_id: credentialId || null,
      });
      setName("");
      setLabel("");
      setCredentialId("");
      await onChange();
    } catch (e) {
      onError(e instanceof ApiError ? e.message : "모델 추가에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }

  async function toggle(m: LlmModelEntry) {
    onError(null);
    try {
      await setLlmModelEnabled(m.id, !m.enabled);
      await onChange();
    } catch (e) {
      onError(e instanceof ApiError ? e.message : "변경에 실패했습니다.");
    }
  }

  async function remove(id: string) {
    onError(null);
    try {
      await deleteLlmModel(id);
      await onChange();
    } catch (e) {
      onError(e instanceof ApiError ? e.message : "삭제에 실패했습니다.");
    }
  }

  return (
    <section className="card flex flex-col gap-4 p-5">
      <h3 className="text-sm font-semibold text-slate-700">생성 모델</h3>

      <div className="flex flex-col gap-3 rounded-lg border border-slate-200 p-4">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <select
            value={provider}
            onChange={(e) => {
              setProvider(e.target.value);
              setCredentialId("");
              setTags([]);
            }}
            className="field-input"
          >
            <option value="">제공자 선택</option>
            {providers.map((p) => (
              <option key={p.provider} value={p.provider}>
                {p.label}
              </option>
            ))}
          </select>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={
              provider === "ollama"
                ? "예: gemma4:e4b"
                : provider
                  ? "예: gpt-4o / claude-sonnet-4-6"
                  : "모델명"
            }
            list="ollama-tags"
            className="field-input"
          />
          <input
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder="표시 이름 (선택)"
            className="field-input"
          />
        </div>

        {provider === "ollama" && (
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={loadTags}
              className="rounded-md border border-slate-300 px-2.5 py-1 text-xs text-slate-600 hover:border-indigo-400 hover:text-indigo-600"
            >
              Ollama 에서 모델 불러오기
            </button>
            {tags.length > 0 && (
              <span className="text-xs text-slate-400">{tags.length}개 — 입력란에서 선택</span>
            )}
            <datalist id="ollama-tags">
              {tags.map((t) => (
                <option key={t} value={t} />
              ))}
            </datalist>
          </div>
        )}

        {needsKey && (
          <select
            value={credentialId}
            onChange={(e) => setCredentialId(e.target.value)}
            className="field-input sm:w-1/2"
          >
            <option value="">API 키 선택 (미지정 시 해당 제공자 키 사용)</option>
            {credsForProvider.map((c) => (
              <option key={c.id} value={c.id}>
                {c.label} ({c.key_preview})
              </option>
            ))}
          </select>
        )}

        <button onClick={add} disabled={busy} className="btn-primary self-start">
          모델 추가
        </button>
      </div>

      {models.length === 0 ? (
        <p className="text-sm text-slate-400">등록된 모델이 없습니다.</p>
      ) : (
        <ul className="divide-y divide-slate-100">
          {models.map((m) => (
            <li key={m.id} className="flex items-center justify-between py-2 text-sm">
              <div className="flex items-center gap-3">
                <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                  {providerLabel(m.provider)}
                </span>
                <span className="font-medium text-slate-700">{m.label}</span>
                <span className="font-mono text-xs text-slate-400">{m.model}</span>
                {!m.enabled && <span className="text-xs text-slate-400">(비활성)</span>}
              </div>
              <div className="flex items-center gap-3">
                <label className="flex items-center gap-1.5 text-xs text-slate-500">
                  <input
                    type="checkbox"
                    checked={m.enabled}
                    onChange={() => toggle(m)}
                    className="h-4 w-4 accent-indigo-600"
                  />
                  사용
                </label>
                <button
                  onClick={() => remove(m.id)}
                  className="rounded px-2 py-1 text-xs text-slate-400 hover:bg-red-50 hover:text-red-600"
                >
                  삭제
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
