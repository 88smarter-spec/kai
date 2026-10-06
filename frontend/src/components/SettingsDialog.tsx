import { useState } from "react";
import { X, PlugZap, ShieldCheck } from "lucide-react";
import { post } from "../services/api";
import type { Settings } from "../types";
export function SettingsDialog({
  settings,
  onSave,
  onClose,
  onStatus,
}: {
  settings: Settings;
  onSave: (s: Settings) => void;
  onClose: () => void;
  onStatus: (s: boolean) => void;
}) {
  const [draft, setDraft] = useState(settings),
    [message, setMessage] = useState(""),
    [ok, setOk] = useState(false),
    [busy, setBusy] = useState(false);
  async function test() {
    setBusy(true);
    setMessage("");
    try {
      const result = await post<{ models: string[] }>("/llm/test", draft);
      setMessage("연결 성공 · " + result.models.join(", "));
      setOk(true);
      onStatus(true);
    } catch (e) {
      setMessage((e as Error).message);
      setOk(false);
      onStatus(false);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="modal-backdrop">
      <section
        className="modal settings-modal"
        role="dialog"
        aria-modal="true"
        aria-label="LLM 설정"
      >
        <header className="modal-header">
          <div>
            <h2>로컬 LLM 설정</h2>
            <p>llama.cpp의 OpenAI-compatible API에 연결합니다.</p>
          </div>
          <button className="icon-button" aria-label="닫기" onClick={onClose}>
            <X size={20} />
          </button>
        </header>
        <div className="modal-body">
          <div className="notice">
            <ShieldCheck size={18} />
            localhost HTTP 주소만 허용 · 외부 API 사용 없음
          </div>
          <label className="field">
            API URL
            <input
              value={draft.url}
              onChange={(e) => setDraft({ ...draft, url: e.target.value })}
            />
          </label>
          <label className="field">
            Model
            <input
              value={draft.model}
              onChange={(e) => setDraft({ ...draft, model: e.target.value })}
              placeholder="비워두면 서버 모델 사용"
            />
          </label>
          <div className="form-row">
            <label className="field">
              Temperature
              <input
                type="number"
                min="0"
                max="1"
                step="0.1"
                value={draft.temperature}
                onChange={(e) =>
                  setDraft({ ...draft, temperature: Number(e.target.value) })
                }
              />
            </label>
            <label className="field">
              Max Tokens
              <input
                type="number"
                min="128"
                max="8192"
                step="128"
                value={draft.max_tokens}
                onChange={(e) =>
                  setDraft({ ...draft, max_tokens: Number(e.target.value) })
                }
              />
            </label>
          </div>
          <button className="button" disabled={busy} onClick={test}>
            <PlugZap size={16} />
            {busy ? "연결 중…" : "연결 확인"}
          </button>
          {message && (
            <div role="status" className={ok ? "success" : "error"}>
              {message}
            </div>
          )}
          <p className="muted small">
            모델 연결이 없어도 데이터 입력·정제·Python 분석·차트는 사용할 수
            있습니다. 설정값만 브라우저에 저장하며 업무 데이터는 저장하지
            않습니다.
          </p>
        </div>
        <footer className="modal-footer">
          <button className="button" onClick={onClose}>
            취소
          </button>
          <button
            className="button primary"
            onClick={() => {
              onSave(draft);
              onClose();
            }}
          >
            설정 저장
          </button>
        </footer>
      </section>
    </div>
  );
}
