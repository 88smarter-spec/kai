import { useEffect, useState } from "react";
import {
  Database,
  Plus,
  ShieldCheck,
  Settings2,
  ChevronDown,
  FileSpreadsheet,
  MoreHorizontal,
  Trash2,
  Pencil,
  ClipboardPaste,
  BarChart3,
  Table2,
  SlidersHorizontal,
  Sparkles,
  Download,
  Activity,
  ArrowUpRight,
  X,
} from "lucide-react";
import { api, post, download } from "./services/api";
import {
  defaultOptions,
  defaultSettings,
  type Dataset,
  type Detail,
  type Plan,
  type AnalysisResult,
  type AutoResult,
  type Settings,
} from "./types";
import {
  ImportDialog,
  sample,
  CleaningOptions,
} from "./components/ImportDialog";
import { DataTable, format } from "./components/DataTable";
import { Chart } from "./components/Chart";
import { AnalysisTools, operationLabels } from "./components/AnalysisTools";
import { SettingsDialog } from "./components/SettingsDialog";
import { ChatPanel } from "./components/ChatPanel";
function savedSettings(): Settings {
  try {
    return {
      ...defaultSettings,
      ...JSON.parse(localStorage.getItem("kai-llm-settings") || "{}"),
    };
  } catch {
    return defaultSettings;
  }
}
export default function App() {
  const [datasets, setDatasets] = useState<Dataset[]>([]),
    [selected, setSelected] = useState(""),
    [detail, setDetail] = useState<Detail | null>(null),
    [tab, setTab] = useState("preview"),
    [importOpen, setImportOpen] = useState(false),
    [settingsOpen, setSettingsOpen] = useState(false),
    [settings, setSettings] = useState(savedSettings),
    [connected, setConnected] = useState(false),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [result, setResult] = useState<AnalysisResult | null>(null),
    [auto, setAuto] = useState<AutoResult | null>(null),
    [source, setSource] = useState("clean"),
    [offset, setOffset] = useState(0),
    [options, setOptions] = useState(defaultOptions),
    [menu, setMenu] = useState(""),
    [notice, setNotice] = useState("");
  const refresh = () => api<Dataset[]>("/datasets").then(setDatasets);
  useEffect(() => {
    refresh().catch((e) => setError(e.message));
  }, []);
  useEffect(() => {
    setOffset(0);
    setSource("clean");
    setResult(null);
    setAuto(null);
    setTab("preview");
    setOptions(defaultOptions);
    setNotice("");
  }, [selected]);
  useEffect(() => {
    if (!selected) {
      setDetail(null);
      return;
    }
    const abort = new AbortController();
    api<Detail>(`/datasets/${selected}?offset=${offset}&source=${source}`, {
      signal: abort.signal,
    })
      .then(setDetail)
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      });
    return () => abort.abort();
  }, [selected, offset, source, datasets]);
  function added(d: Dataset) {
    setDatasets((prev) => [...prev, d]);
    setSelected(d.id);
  }
  async function run(plan: Plan) {
    setBusy(true);
    setError("");
    try {
      const r = await post<AnalysisResult>("/analysis", plan);
      setResult(r);
      setTab("analysis");
      setNotice("Python 분석 완료");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function runAuto() {
    if (!detail) return;
    setBusy(true);
    setError("");
    try {
      const a = await post<AutoResult>(`/datasets/${detail.id}/auto`, {});
      setAuto(a);
      setTab("dashboard");
      setNotice("자동 분석 완료");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function remove(d: Dataset) {
    if (
      !window.confirm(
        `“${d.name}” 데이터셋을 삭제할까요? 메모리에서 제거됩니다.`,
      )
    )
      return;
    try {
      await api(`/datasets/${d.id}`, { method: "DELETE" });
      const list = await api<Dataset[]>("/datasets");
      setDatasets(list);
      if (selected === d.id) setSelected(list[0]?.id || "");
      setMenu("");
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function rename(d: Dataset) {
    const name = window.prompt("새 데이터셋 이름", d.name);
    if (!name) return;
    try {
      await api(`/datasets/${d.id}`, {
        method: "PATCH",
        body: JSON.stringify({ name }),
      });
      await refresh();
      setMenu("");
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function clean() {
    if (!detail) return;
    setBusy(true);
    try {
      await post(`/datasets/${detail.id}/clean`, options);
      await refresh();
      setResult(null);
      setAuto(null);
      setNotice("정제 완료 · 원본과 비교할 수 있습니다.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function loadSample() {
    setBusy(true);
    try {
      added(
        await post<Dataset>("/datasets/paste", {
          name: "인력계획 샘플",
          text: sample,
        }),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function saveResult() {
    if (!result) return;
    const name = window.prompt("파생 데이터셋 이름", "분석 결과");
    if (!name) return;
    setBusy(true);
    try {
      added(await post<Dataset>("/analysis/save", { name, plan: result.plan }));
      setNotice("전체 분석 결과가 메모리 데이터셋으로 등록되었습니다.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const showResult = (r: AnalysisResult) => {
    setResult(r);
    setTab("analysis");
  };
  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-mark">
          <BarChart3 size={22} />
        </div>
        <div className="brand">
          <strong>
            Excel Data <span>분석 시스템</span>
          </strong>
          <span className="brand-subtitle">LOCAL DATA WORKSPACE</span>
        </div>
        <div className="topbar-right">
          <span className="offline-badge">
            <ShieldCheck size={14} />
            오프라인 · 로컬 처리
          </span>
          <button
            className="button compact"
            aria-label="LLM 설정"
            onClick={() => setSettingsOpen(true)}
          >
            <Settings2 size={15} />
            LLM 설정
          </button>
          <span className="version">V1.0</span>
        </div>
      </header>
      <div className="workspace">
        <aside className="sidebar">
          <div className="sidebar-heading">
            <span>WORKSPACE</span>
            <ChevronDown size={14} />
          </div>
          <div className="dataset-title">
            <h2>
              <Database size={16} />
              데이터셋
            </h2>
            <span>{datasets.length}</span>
          </div>
          <button className="add-button" onClick={() => setImportOpen(true)}>
            <Plus size={16} />
            데이터 추가
          </button>
          <div className="dataset-list">
            {datasets.length === 0 ? (
              <p className="sidebar-empty">
                등록된 데이터가 없습니다.
                <br />
                Excel 데이터를 추가해보세요.
              </p>
            ) : (
              datasets.map((d) => (
                <div
                  className={
                    "dataset-item " + (selected === d.id ? "selected" : "")
                  }
                  key={d.id}
                >
                  <button
                    className="dataset-select"
                    onClick={() => setSelected(d.id)}
                  >
                    <FileSpreadsheet size={18} />
                    <span>
                      <strong>{d.name}</strong>
                      <small>
                        {d.row_count.toLocaleString()}행 · {d.column_count}열
                      </small>
                    </span>
                  </button>
                  <button
                    className="dataset-more"
                    aria-label={`${d.name} 관리`}
                    onClick={() => setMenu(menu === d.id ? "" : d.id)}
                  >
                    <MoreHorizontal size={17} />
                  </button>
                  {menu === d.id && (
                    <div className="dataset-menu">
                      <button onClick={() => rename(d)}>
                        <Pencil size={13} />
                        이름 변경
                      </button>
                      <button onClick={() => remove(d)}>
                        <Trash2 size={13} />
                        삭제
                      </button>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
          <div className="sidebar-bottom">
            <ShieldCheck size={21} />
            <strong>데이터는 이 PC 안에만</strong>
            <p>
              입력한 데이터는 메모리에서 처리합니다. 서버 종료 시 삭제됩니다.
            </p>
            <span>
              <span className="status-dot" />
              LOCALHOST ONLY
            </span>
          </div>
        </aside>
        <main className="main-panel">
          {error && (
            <div role="alert" className="error global-error">
              <span>{error}</span>
              <button aria-label="오류 닫기" onClick={() => setError("")}>
                <X size={16} />
              </button>
            </div>
          )}
          {!detail ? (
            <div className="welcome">
              <span className="eyebrow">YOUR DATA, YOUR WORKSPACE</span>
              <div className="welcome-icon">
                <FileSpreadsheet size={39} />
              </div>
              <h1>
                Excel 데이터를,
                <br />
                <span>의사결정의 근거로.</span>
              </h1>
              <p>
                복잡한 파일 업로드 없이 필요한 범위를 복사하세요.
                <br />
                정확한 Python 분석과 로컬 AI 해석을 한 곳에서.
              </p>
              <button
                className="button primary large"
                onClick={() => setImportOpen(true)}
              >
                <ClipboardPaste size={18} />
                Excel 데이터 붙여넣기
              </button>
              <button
                className="text-button"
                disabled={busy}
                onClick={loadSample}
              >
                샘플 데이터로 시작하기 <ArrowUpRight size={15} />
              </button>
              <div className="welcome-features">
                <div>
                  <ClipboardPaste size={20} />
                  <strong>복사해서 바로 분석</strong>
                  <span>Excel Ctrl+C → Ctrl+V</span>
                </div>
                <div>
                  <Activity size={20} />
                  <strong>검증 가능한 계산</strong>
                  <span>Python 기반 안전한 도구</span>
                </div>
                <div>
                  <ShieldCheck size={20} />
                  <strong>완전한 로컬 처리</strong>
                  <span>외부 API · 원본 파일 읽기 없음</span>
                </div>
              </div>
            </div>
          ) : (
            <>
              <section className="workspace-header">
                <div>
                  <div className="breadcrumb">
                    데이터셋 <span>/</span> 분석 워크스페이스
                  </div>
                  <h1>
                    {detail.name}
                    <span className="data-badge" aria-hidden="true">
                      DATASET
                    </span>
                  </h1>
                  <p>
                    {detail.row_count.toLocaleString()}개의 행과{" "}
                    {detail.column_count}개의 컬럼 · 메모리 데이터셋
                  </p>
                </div>
                <button
                  className="button primary"
                  disabled={busy}
                  onClick={runAuto}
                >
                  <Sparkles size={16} />
                  전체 자동 분석
                </button>
              </section>
              <section className="stat-grid">
                <div className="stat-card">
                  <span>전체 행</span>
                  <strong>
                    {detail.row_count.toLocaleString()}
                    <small>rows</small>
                  </strong>
                  <div className="stat-icon blue">
                    <Table2 size={18} />
                  </div>
                </div>
                <div className="stat-card">
                  <span>분석 컬럼</span>
                  <strong>
                    {detail.column_count}
                    <small>columns</small>
                  </strong>
                  <div className="stat-icon teal">
                    <Database size={18} />
                  </div>
                </div>
                <div className="stat-card">
                  <span>결측 셀</span>
                  <strong>
                    {detail.profile.null_count.toLocaleString()}
                    <small>cells</small>
                  </strong>
                  <div className="stat-icon amber">
                    <SlidersHorizontal size={18} />
                  </div>
                </div>
                <div className="stat-card">
                  <span>중복 추가 행</span>
                  <strong>
                    {detail.profile.duplicates.toLocaleString()}
                    <small>rows</small>
                  </strong>
                  <div className="stat-icon violet">
                    <Activity size={18} />
                  </div>
                </div>
              </section>
              <div className="tabs">
                <button
                  className={tab === "preview" ? "active" : ""}
                  onClick={() => setTab("preview")}
                >
                  <Table2 size={16} />
                  데이터 Preview
                </button>
                <button
                  className={tab === "profile" ? "active" : ""}
                  onClick={() => setTab("profile")}
                >
                  <SlidersHorizontal size={16} />
                  정제 · 프로파일
                </button>
                <button
                  className={tab === "analysis" ? "active" : ""}
                  onClick={() => setTab("analysis")}
                >
                  <BarChart3 size={16} />
                  기본 분석
                </button>
                <button
                  className={tab === "dashboard" ? "active" : ""}
                  onClick={() => setTab("dashboard")}
                >
                  <Sparkles size={16} />
                  Dashboard
                </button>
              </div>
              {notice && (
                <div role="status" className="notice slim">
                  {notice}
                </div>
              )}
              <div className="tab-content">
                {tab === "preview" && (
                  <>
                    <div className="section-heading">
                      <div>
                        <h2>데이터 미리보기</h2>
                        <p>
                          한 페이지에 50행 표시 · 원본은 변환 전 데이터입니다.
                        </p>
                      </div>
                      <div className="segmented small">
                        <button
                          className={source === "clean" ? "active" : ""}
                          onClick={() => {
                            setSource("clean");
                            setOffset(0);
                          }}
                        >
                          정제 결과
                        </button>
                        <button
                          className={source === "raw" ? "active" : ""}
                          onClick={() => {
                            setSource("raw");
                            setOffset(0);
                          }}
                        >
                          원본
                        </button>
                      </div>
                    </div>
                    <DataTable
                      rows={detail.preview}
                      columns={detail.columns}
                      total={detail.preview_total}
                      offset={offset}
                      onPage={setOffset}
                    />
                    <div className="recommendation-section">
                      <div className="section-heading">
                        <h2>
                          <Sparkles size={16} />
                          추천 분석
                        </h2>
                        <span className="muted small">
                          컬럼 구조 기반 추천 · Python 계산
                        </span>
                      </div>
                      <div className="recommendation-grid">
                        {detail.recommendations.slice(0, 8).map((r, i) => (
                          <button
                            key={i}
                            disabled={busy}
                            onClick={() => {
                              if (
                                r.plan.operation === "join" &&
                                !window.confirm(
                                  "JOIN KEY: " +
                                    r.plan.join_keys?.join(", ") +
                                    "\n이 키로 결합할까요?",
                                )
                              )
                                return;
                              void run(r.plan);
                            }}
                          >
                            <span className="recommendation-number">
                              {String(i + 1).padStart(2, "0")}
                            </span>
                            <span>{r.title}</span>
                            <ArrowUpRight size={16} />
                          </button>
                        ))}
                      </div>
                    </div>
                  </>
                )}
                {tab === "profile" && (
                  <>
                    <section className="card">
                      <div className="section-heading">
                        <div>
                          <h2>데이터 정제</h2>
                          <p>
                            원본을 보존한 채 옵션을 적용합니다. 재적용 시 기존
                            분석 결과가 초기화됩니다.
                          </p>
                        </div>
                        <button
                          className="button primary"
                          onClick={clean}
                          disabled={busy}
                        >
                          정제 적용
                        </button>
                      </div>
                      <CleaningOptions
                        options={options}
                        onChange={setOptions}
                      />
                      <p className="muted small">
                        제거한 행 {detail.cleaning.removed_rows} · 제거한 열{" "}
                        {detail.cleaning.removed_columns} · 합계/소계 후보{" "}
                        {detail.cleaning.total_candidates} · 헤더 시작{" "}
                        {detail.cleaning.header_start || 1}행
                      </p>
                      {detail.cleaning.warnings.map((w, i) => (
                        <p className="notice" key={i}>
                          {w}
                        </p>
                      ))}
                    </section>
                    <section className="card">
                      <div className="section-heading">
                        <h2>컬럼 프로파일</h2>
                        <span className="muted small">
                          숫자 {detail.profile.numeric_columns.length} · 날짜{" "}
                          {detail.profile.date_columns.length} · 범주{" "}
                          {detail.profile.categorical_columns.length}
                        </span>
                      </div>
                      <DataTable
                        rows={detail.profile.columns.map((c) => ({
                          컬럼: c.name,
                          타입: c.dtype,
                          고유값: c.unique,
                          결측: c.null_count,
                          "결측률 (%)": c.null_ratio * 100,
                          최소: c.min,
                          최대: c.max,
                          평균: c.mean,
                          중앙값: c.median,
                          표준편차: c.std,
                          "상위 값": c.top_values
                            .map((v) => `${format(v.value)} (${v.count})`)
                            .join(", "),
                        }))}
                        columns={[
                          "컬럼",
                          "타입",
                          "고유값",
                          "결측",
                          "결측률 (%)",
                          "최소",
                          "최대",
                          "평균",
                          "중앙값",
                          "표준편차",
                          "상위 값",
                        ]}
                      />
                    </section>
                  </>
                )}
                {tab === "analysis" && (
                  <>
                    <AnalysisTools
                      detail={detail}
                      datasets={datasets}
                      onRun={run}
                      busy={busy}
                    />
                    {result ? (
                      <>
                        <div className="section-heading">
                          <div>
                            <h2>{operationLabels[result.operation]} 결과</h2>
                            <p>
                              {result.total_rows.toLocaleString()}행 ·{" "}
                              {result.truncated
                                ? "상위 500행 제공"
                                : "전체 결과 제공"}
                            </p>
                          </div>
                          <button
                            className="button compact"
                            disabled={busy}
                            onClick={saveResult}
                          >
                            <Plus size={14} />
                            결과를 데이터셋으로
                          </button>
                          <button
                            className="button compact"
                            onClick={() =>
                              download(
                                "분석결과.json",
                                JSON.stringify(result, null, 2),
                                "application/json",
                              )
                            }
                          >
                            <Download size={14} />
                            결과 저장
                          </button>
                        </div>
                        {result.warnings.map((w, i) => (
                          <p className="notice" key={i}>
                            {w}
                          </p>
                        ))}
                        <Chart result={result} />
                        <DataTable
                          rows={result.rows}
                          columns={result.columns}
                          total={result.total_rows}
                        />
                        <details className="result-evidence">
                          <summary>계산 근거 · 분석 계획</summary>
                          <pre>
                            {JSON.stringify(
                              { plan: result.plan, details: result.details },
                              null,
                              2,
                            )}
                          </pre>
                        </details>
                      </>
                    ) : (
                      <div className="analysis-empty">
                        <BarChart3 size={28} />
                        <h3>분석할 도구와 컬럼을 선택하세요.</h3>
                        <p>
                          모든 수치 계산은 Python에서 실행합니다. AI 연결은
                          필요하지 않습니다.
                        </p>
                      </div>
                    )}
                  </>
                )}
                {tab === "dashboard" &&
                  (auto ? (
                    <>
                      <section className="card summary-card">
                        <span className="eyebrow">PYTHON ANALYSIS</span>
                        <h2>핵심 요약</h2>
                        {auto.summary.map((s, i) => (
                          <p key={i}>{s}</p>
                        ))}
                        {auto.notes.map((s, i) => (
                          <p className="muted small" key={i}>
                            {s}
                          </p>
                        ))}
                      </section>
                      {auto.analyses.map((a, i) => (
                        <section className="card" key={i}>
                          <div className="section-heading">
                            <h2>{a.title}</h2>
                            <button
                              className="text-button"
                              onClick={() => showResult(a.result)}
                            >
                              상세 보기 <ArrowUpRight size={14} />
                            </button>
                          </div>
                          {a.result.chart && <Chart result={a.result} />}
                          <DataTable
                            rows={a.result.rows}
                            columns={a.result.columns}
                            total={a.result.total_rows}
                          />
                          {a.result.warnings.map((w, j) => (
                            <p className="notice" key={j}>
                              {w}
                            </p>
                          ))}
                        </section>
                      ))}
                      {auto.skipped.length > 0 && (
                        <div className="notice">
                          실행하지 못한 분석:{" "}
                          {auto.skipped
                            .map((x) => x.title + " · " + x.reason)
                            .join(" / ")}
                        </div>
                      )}
                    </>
                  ) : (
                    <div className="analysis-empty">
                      <Sparkles size={30} />
                      <h3>데이터 전체를 한 번에 살펴보세요.</h3>
                      <p>구조·품질·집계·추세·이상치·상관관계를 확인합니다.</p>
                      <button
                        className="button primary"
                        onClick={runAuto}
                        disabled={busy}
                      >
                        전체 자동 분석
                      </button>
                    </div>
                  ))}
              </div>
            </>
          )}
        </main>
        <ChatPanel
          detail={detail}
          settings={settings}
          connected={connected}
          onSettings={() => setSettingsOpen(true)}
          onResult={showResult}
        />
      </div>
      {importOpen && (
        <ImportDialog onClose={() => setImportOpen(false)} onAdded={added} />
      )}{" "}
      {settingsOpen && (
        <SettingsDialog
          settings={settings}
          onSave={(s) => {
            setSettings(s);
            setConnected(false);
            localStorage.setItem("kai-llm-settings", JSON.stringify(s));
          }}
          onClose={() => setSettingsOpen(false)}
          onStatus={setConnected}
        />
      )}
    </div>
  );
}
