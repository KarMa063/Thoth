import { getAuthorTrait, TAB_META } from "../../constants/dashboard";
import LoadingPipeline from "./LoadingPipeline";

export default function OutputPanel({
  activeTab,
  author,
  currentStep,
  elapsedTime,
  lang,
  loading,
  microcopyIndex,
  onClear,
  onCopy,
  out,
  wordCount,
}) {
  return (
    <section className="editor-panel" aria-label="Generated output">
      <OutputHeader
        activeTab={activeTab}
        author={author}
        elapsedTime={elapsedTime}
        lang={lang}
        loading={loading}
        wordCount={wordCount}
      />

      <div className="output-body">
        {loading ? (
          <LoadingPipeline
            activeTab={activeTab}
            currentStep={currentStep}
            microcopyIndex={microcopyIndex}
          />
        ) : out ? (
          <div className="output-text">{out}</div>
        ) : (
          <EmptyOutput activeTab={activeTab} />
        )}
      </div>

      {out && !loading && (
        <div className="editor-footer output-actions">
          <button className="btn ghost btn-compact" type="button" onClick={onCopy}>
            Copy
          </button>
          <button className="btn ghost btn-compact" type="button" onClick={onClear}>
            Clear
          </button>
        </div>
      )}
    </section>
  );
}

function OutputHeader({ activeTab, author, elapsedTime, lang, loading, wordCount }) {
  if (!loading) {
    return (
      <div className="editor-panel-header">
        <span>{activeTab === "analyze" ? "Analysis Results" : "Output"}</span>
        {lang && (
          <span className="language-pill">
            {lang === "ne" ? "Nepali" : "English"}
          </span>
        )}
      </div>
    );
  }

  return (
    <div className="editor-panel-header output-header-loading">
      <div className="output-header-row">
        <span className="active-panel-label">
          {activeTab === "analyze" ? "Analyzing" : "Generating"}
        </span>
        <span className="elapsed-time">{elapsedTime}s</span>
      </div>

      <div className="meta-chip-row">
        {activeTab !== "analyze" && author && (
          <MetaChip label="Author" value={author} />
        )}
        <MetaChip label="Mode" value={TAB_META[activeTab].label} />
        <MetaChip label="Words" value={wordCount} />
      </div>

      {activeTab !== "analyze" && author && (
        <div className="author-trait-box">
          {getAuthorTrait(author)}
        </div>
      )}
    </div>
  );
}

function MetaChip({ label, value }) {
  return (
    <div className="meta-chip">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function EmptyOutput({ activeTab }) {
  return (
    <div className="output-empty">
      <div className="output-empty-glyph">Θ</div>
      <p>
        {activeTab === "analyze"
          ? "Analysis results will appear here"
          : "Your generated text will appear here"}
      </p>
      <p>
        {activeTab !== "analyze"
          ? "Paste text, choose an author, and run the selected mode."
          : "Paste text and run analysis."}
      </p>
    </div>
  );
}
