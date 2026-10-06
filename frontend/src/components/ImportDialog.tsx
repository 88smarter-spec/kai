import { useState } from "react";
import { ClipboardPaste, Upload, X, FileText } from "lucide-react";
import { api, post } from "../services/api";
import { defaultOptions, type CleanOptions, type Dataset } from "../types";
export const sample =
  "사업\t월\t가용인력\t소요인력\t계획공수\t실적공수\t생산대수\t잔업률\nKF-21\t1월\t210\t230\t12000\t12500\t4\t15\nKF-21\t2월\t215\t228\t13000\t14100\t5\t18\nKF-21\t3월\t218\t240\t14000\t15700\t5\t19\nT-50\t1월\t160\t155\t8500\t8300\t3\t8\nT-50\t2월\t158\t160\t8700\t9000\t3\t10\nLAH\t1월\t130\t138\t7600\t7900\t4\t12";
export const optionLabels: Record<keyof CleanOptions, string> = {
  empty_rows: "빈 행 제거",
  empty_columns: "빈 열 제거",
  exclude_totals: "합계·소계 행 제외",
  numbers: "숫자 자동 변환",
  dates: "날짜 자동 변환",
  percentages: "% 값 비율 변환",
};
export function CleaningOptions({
  options,
  onChange,
}: {
  options: CleanOptions;
  onChange: (o: CleanOptions) => void;
}) {
  return (
    <div className="check-grid">
      {(Object.keys(optionLabels) as (keyof CleanOptions)[]).map((key) => (
        <label key={key}>
          <input
            type="checkbox"
            checked={options[key]}
            onChange={(e) => onChange({ ...options, [key]: e.target.checked })}
          />
          {optionLabels[key]}
        </label>
      ))}
    </div>
  );
}
export function ImportDialog({
  onClose,
  onAdded,
}: {
  onClose: () => void;
  onAdded: (d: Dataset) => void;
}) {
  const [mode, setMode] = useState("paste"),
    [name, setName] = useState(""),
    [text, setText] = useState(""),
    [file, setFile] = useState<File | null>(null),
    [header, setHeader] = useState(""),
    [headerRows, setHeaderRows] = useState(1),
    [delimiter, setDelimiter] = useState("tab"),
    [options, setOptions] = useState(defaultOptions),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function submit() {
    setError("");
    setBusy(true);
    try {
      let d: Dataset;
      if (mode === "paste")
        d = await post("/datasets/paste", {
          name: name || "새 데이터셋",
          text,
          header_start: header ? Number(header) : null,
          header_rows: headerRows,
          delimiter,
          options,
        });
      else {
        if (!file) throw new Error("TXT/TSV/CSV 파일을 선택해주세요.");
        const form = new FormData();
        form.set("file", file);
        form.set("name", name);
        form.set("header_rows", String(headerRows));
        form.set("options", JSON.stringify(options));
        if (header) form.set("header_start", header);
        d = await api("/datasets/upload", { method: "POST", body: form });
      }
      onAdded(d);
      onClose();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="modal-backdrop">
      <section
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-label="데이터 추가"
      >
        <header className="modal-header">
          <div>
            <h2>데이터 추가</h2>
            <p>Excel에서 복사한 데이터 또는 텍스트 파일을 가져옵니다.</p>
          </div>
          <button className="icon-button" onClick={onClose} aria-label="닫기">
            <X size={20} />
          </button>
        </header>
        <div className="modal-body">
          <div className="segmented">
            <button
              className={mode === "paste" ? "active" : ""}
              onClick={() => setMode("paste")}
            >
              <ClipboardPaste size={16} />
              Excel 붙여넣기
            </button>
            <button
              className={mode === "file" ? "active" : ""}
              onClick={() => setMode("file")}
            >
              <Upload size={16} />
              텍스트 파일
            </button>
          </div>
          <label className="field">
            데이터셋 이름
            <input
              autoFocus
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="예: 2027년 인력계획"
              maxLength={100}
            />
          </label>
          {mode === "paste" ? (
            <>
              <div className="input-heading">
                <label htmlFor="clipboard">Excel 데이터 붙여넣기</label>
                <button
                  className="text-button"
                  onClick={() => {
                    setText(sample);
                    setName("인력계획 샘플");
                  }}
                >
                  샘플 데이터 사용
                </button>
              </div>
              <textarea
                id="clipboard"
                className="paste-area"
                value={text}
                onChange={(e) => setText(e.target.value)}
                onPaste={(e) => {
                  e.preventDefault();
                  setText(e.clipboardData.getData("text/plain"));
                }}
                placeholder={
                  "Excel에서 범위를 선택 → Ctrl+C → 여기에 Ctrl+V\n\n사업\t월\t가용인력\t소요인력\nKF-21\t1월\t210\t230"
                }
              />
              <div className="muted small">
                TAB으로 열을 구분합니다. 붙여넣은 텍스트는 등록 후 자동
                인식됩니다.
              </div>
            </>
          ) : (
            <label className="upload-zone">
              <FileText size={32} />
              <strong>{file ? file.name : "텍스트 파일을 선택하세요"}</strong>
              <span>TXT · TSV · CSV / 최대 50MB / UTF-8 · CP949 · EUC-KR</span>
              <input
                type="file"
                accept=".txt,.tsv,.csv"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f && !/\.(txt|tsv|csv)$/i.test(f.name)) {
                    setError(
                      "Excel 파일은 지원하지 않습니다. TXT/TSV로 입력해주세요.",
                    );
                    return;
                  }
                  setFile(f || null);
                  setError("");
                }}
              />
            </label>
          )}
          <div className="form-row">
            <label className="field">
              헤더 시작 행
              <input
                type="number"
                min="1"
                max="100"
                value={header}
                onChange={(e) => setHeader(e.target.value)}
                placeholder="자동 감지"
              />
            </label>
            <label className="field">
              헤더 행 개수
              <select
                value={headerRows}
                onChange={(e) => setHeaderRows(Number(e.target.value))}
              >
                <option value="1">1행</option>
                <option value="2">2행 결합</option>
                <option value="3">3행 결합</option>
              </select>
            </label>
            {mode === "paste" && (
              <label className="field">
                구분자
                <select
                  value={delimiter}
                  onChange={(e) => setDelimiter(e.target.value)}
                >
                  <option value="tab">TAB (Excel / TSV)</option>
                  <option value="comma">쉼표 (CSV)</option>
                </select>
              </label>
            )}
          </div>
          <details>
            <summary>정제 옵션</summary>
            <CleaningOptions options={options} onChange={setOptions} />
            <p className="muted small">
              15% → 0.15. 문자가 섞인 숫자 컬럼은 원문을 유지하고 경고합니다.
            </p>
          </details>
          {error && (
            <div role="alert" className="error">
              {error}
            </div>
          )}
        </div>
        <footer className="modal-footer">
          <span className="muted small">원본 Excel 파일은 읽지 않습니다.</span>
          <button className="button" onClick={onClose}>
            취소
          </button>
          <button
            className="button primary"
            disabled={busy || (mode === "paste" && !text.trim())}
            onClick={submit}
          >
            {busy ? "처리 중…" : "데이터 등록"}
          </button>
        </footer>
      </section>
    </div>
  );
}
