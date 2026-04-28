import AuthorSelect from "./AuthorSelect";

export default function EditorPanel({
  activeTab,
  author,
  authors,
  charCount,
  lang,
  loading,
  onAction,
  onAuthorChange,
  onCancel,
  onTextChange,
  text,
  wordCount,
}) {
  const needsAuthor = activeTab !== "analyze";
  const disabled = loading || !text.trim() || (needsAuthor && !author);
  const panelLabel = activeTab === "analyze" ? "Text to Analyze" : activeTab === "continue" ? "Start Text" : "Input";
  const placeholder = activeTab === "continue"
    ? "Start your story here..."
    : "Paste your text here (English or Nepali)...";

  return (
    <section className={`editor-panel ${loading ? "is-muted" : ""}`} aria-label="Text input">
      <div className="editor-panel-header">
        <span>{panelLabel}</span>
        {needsAuthor && (
          <AuthorSelect
            authors={authors}
            value={author}
            onChange={onAuthorChange}
            disabled={loading}
          />
        )}
      </div>

      <textarea
        className="editor-textarea"
        placeholder={placeholder}
        value={text}
        onChange={(event) => onTextChange(event.target.value)}
        disabled={loading}
      />

      <div className="editor-footer">
        <span className="word-count">
          {wordCount} words / {charCount} chars
          {lang && (
            <span className="detected-language">
              {lang === "ne" ? "Nepali detected" : "English detected"}
            </span>
          )}
        </span>

        <div className="editor-actions">
          {loading && (
            <button className="btn ghost btn-compact" type="button" onClick={onCancel}>
              Cancel
            </button>
          )}
          <button className="btn primary btn-compact" type="button" onClick={onAction} disabled={disabled}>
            {loading ? (
              <span className="button-loading">
                <span className="button-spinner" aria-hidden="true" />
                Generating...
              </span>
            ) : (
              activeTab === "analyze" ? "Analyze" : activeTab === "continue" ? "Continue" : "Rewrite"
            )}
          </button>
        </div>
      </div>
    </section>
  );
}
