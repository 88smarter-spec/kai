import { useState, useEffect, useRef } from "react";
import {
  Sparkles,
  Send,
  FileText,
  Check,
  Download,
  Settings2,
} from "lucide-react";
import { post, download } from "../services/api";
import type { Plan, Settings, Detail, AnalysisResult } from "../types";
import { operationLabels } from "./AnalysisTools";
interface Message {
  role: "user" | "assistant";
  text: string;
  plan?: Plan;
  question?: string;
  executed?: boolean;
  report?: boolean;
}
interface Response {
  stage: string;
  plan?: Plan;
  message?: string;
  answer?: string;
  warning?: string;
  result?: AnalysisResult;
  evidence?: unknown;
}
export function ChatPanel({
  detail,
  settings,
  connected,
  onSettings,
  onResult,
}: {
  detail: Detail | null;
  settings: Settings;
  connected: boolean;
  onSettings: () => void;
  onResult: (r: AnalysisResult) => void;
}) {
  const [messages, setMessages] = useState<Message[]>([]),
    [question, setQuestion] = useState(""),
    [busy, setBusy] = useState(false);
  const scroll = useRef<HTMLDivElement>(null);
  useEffect(() => {
    setMessages([]);
    setQuestion("");
  }, [detail?.id]);
  useEffect(() => {
    scroll.current?.scrollTo({
      top: scroll.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, busy]);
  async function ask(report = false) {
    if (!detail || busy || (!report && !question.trim())) return;
    const q = report
      ? "경영진에게 보고할 핵심 이슈와 대응 필요사항을 근거와 함께 한국어 보고서로 정리해주세요."
      : question.trim();
    setQuestion("");
    setBusy(true);
    setMessages((m) => [
      ...m,
      { role: "user", text: report ? "경영진 보고서 생성" : q },
    ]);
    try {
      const res = await post<Response>("/chat", {
        question: q,
        dataset: detail.id,
        settings,
        report,
      });
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          text: res.message || res.answer || "응답이 없습니다.",
          plan: res.plan,
          question: q,
          report,
        },
      ]);
    } catch (e) {
      setMessages((m) => [
        ...m,
        { role: "assistant", text: (e as Error).message },
      ]);
    } finally {
      setBusy(false);
    }
  }
  async function execute(index: number) {
    const item = messages[index];
    if (!detail || !item.plan || busy) return;
    setBusy(true);
    try {
      const res = await post<Response>("/chat", {
        question: item.question,
        dataset: detail.id,
        settings,
        execute: true,
        plan: item.plan,
      });
      setMessages((m) =>
        m
          .map((v, i) => (i === index ? { ...v, executed: true } : v))
          .concat({
            role: "assistant",
            text:
              (res.answer || "") +
              (res.warning ? "\n\n확인사항: " + res.warning : ""),
          }),
      );
      if (res.result) onResult(res.result);
    } catch (e) {
      setMessages((m) => [
        ...m,
        { role: "assistant", text: (e as Error).message },
      ]);
    } finally {
      setBusy(false);
    }
  }
  const suggestions = [
    "사업별 인력 부족 구간 찾아줘",
    "월별 가용인력 대비 소요인력 GAP 분석해줘",
    "이 데이터에서 특이한 점을 찾아줘",
  ];
  return (
    <aside className="chat-panel">
      <div className="chat-header">
        <div className="ai-icon">
          <Sparkles size={19} />
        </div>
        <div>
          <h2>AI Analyst</h2>
          <span className="muted small">Local Qwen · 한국어 분석</span>
        </div>
        <button
          className="icon-button"
          onClick={onSettings}
          aria-label="AI 연결 설정"
        >
          <Settings2 size={17} />
        </button>
      </div>
      <div className={"llm-status " + (connected ? "connected" : "")}>
        <span className="status-dot" />
        {connected ? "로컬 AI 연결 확인됨" : "로컬 AI 연결 대기"}
        <button onClick={onSettings}>설정</button>
      </div>
      <div className="chat-messages" ref={scroll}>
        {messages.length === 0 ? (
          <div className="chat-welcome">
            <Sparkles size={27} />
            <h3>데이터에 질문하세요.</h3>
            <p>
              Python이 정확하게 계산하고,
              <br />
              로컬 AI가 결과를 해석합니다.
            </p>
            <div className="suggestion-list">
              {suggestions.map((s) => (
                <button
                  key={s}
                  disabled={!detail}
                  onClick={() => setQuestion(s)}
                >
                  {s}
                  <span>↗</span>
                </button>
              ))}
            </div>
            <div className="chat-safety">
              <Check size={14} />
              검증된 분석 도구만 실행
              <br />
              <Check size={14} />
              원본 전체 데이터 전달 없음
            </div>
          </div>
        ) : (
          messages.map((m, i) => (
            <div key={i} className={"chat-message " + m.role}>
              <span className="message-author">
                {m.role === "user" ? "사용자" : "AI Analyst"}
              </span>
              <div className="message-text">{m.text}</div>
              {m.plan && (
                <div className="plan-preview">
                  <strong>{operationLabels[m.plan.operation]}</strong>
                  {m.plan.join_keys?.length ? (
                    <p>JOIN KEY: {m.plan.join_keys.join(", ")}</p>
                  ) : null}
                  <p>
                    컬럼:{" "}
                    {(m.plan.columns || Object.keys(m.plan.metrics || {})).join(
                      ", ",
                    ) || "전체"}
                  </p>
                  {m.plan.group_by?.length ? (
                    <p>그룹: {m.plan.group_by.join(", ")}</p>
                  ) : null}
                  <details>
                    <summary>JSON 계획 확인</summary>
                    <pre>{JSON.stringify(m.plan, null, 2)}</pre>
                  </details>
                  <button
                    className="button primary"
                    disabled={busy || m.executed}
                    onClick={() => execute(i)}
                  >
                    <Check size={14} />
                    {m.executed ? "실행 완료" : "계획 확인 후 실행"}
                  </button>
                </div>
              )}
              {m.role === "assistant" && !m.plan && (
                <button
                  className="text-button small"
                  onClick={() =>
                    download(
                      m.report ? "경영진_보고서.txt" : "분석_해석.txt",
                      m.text,
                    )
                  }
                >
                  <Download size={12} />
                  텍스트 저장
                </button>
              )}
            </div>
          ))
        )}
        {busy && (
          <div className="chat-loading">
            <span className="spinner" />
            로컬 AI 처리 중…
          </div>
        )}
      </div>
      <div className="chat-compose">
        <button
          className="report-button"
          disabled={!detail || busy}
          onClick={() => ask(true)}
        >
          <FileText size={15} />
          경영진 보고서 생성
        </button>
        <div className="chat-input">
          <textarea
            aria-label="AI 질문"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            disabled={!detail || busy}
            placeholder={
              detail
                ? "데이터에 대해 질문하세요…"
                : "먼저 데이터셋을 추가하세요"
            }
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void ask();
              }
            }}
          />
          <button
            aria-label="질문 전송"
            disabled={!detail || busy || !question.trim()}
            onClick={() => ask()}
          >
            <Send size={17} />
          </button>
        </div>
        <p>
          Enter 전송 · Shift+Enter 줄바꿈
          <br />
          해석과 원인 후보는 계산 근거와 함께 검토하세요.
        </p>
      </div>
    </aside>
  );
}
