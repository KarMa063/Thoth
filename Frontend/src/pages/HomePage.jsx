import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";

const API_BASE = "http://127.0.0.1:8000";

export default function HomePage() {
  const { user } = useAuth();
  const [text, setText] = useState("");
  const [author, setAuthor] = useState("");
  const [authors, setAuthors] = useState([]);
  const [loading, setLoading] = useState(false);
  const [out, setOut] = useState("");
  const [lang, setLang] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/authors`);
        const data = await res.json();
        setAuthors(data.authors || []);
      } catch (e) {
        console.error(e);
        setAuthors([]);
      }
    })();
  }, []);

  async function handleRewrite() {
    if (!text.trim() || !author) return alert("Enter text and choose an author.");
    setLoading(true);
    setOut("");
    setLang("");

    try {
      const res = await fetch(`${API_BASE}/rewrite`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, author }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || "Rewrite failed");

      setOut(data.rewritten || "");
      setLang(data.language || "");
    } catch (err) {
      console.error(err);
      setOut(`❌ Rewrite error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="container" style={{ marginTop: 40, maxWidth: "1200px" }}>
      <header style={{ marginBottom: 40, textAlign: "center" }}>
        <h1 className="fade-in">
          Welcome back, <span className="gradient-text">{user?.name || "Writer"}</span>! ✍️
        </h1>
        <p className="small fade-in" style={{ animationDelay: "0.1s" }}>
          Author-tone rewriting using multilingual RAG (English + Nepali)
        </p>
      </header>

      <div className="grid grid-2 fade-in" style={{ animationDelay: "0.2s" }}>
        <div className="panel" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h2>Input</h2>
            <select
              className="select"
              value={author}
              onChange={(e) => setAuthor(e.target.value)}
              style={{ width: "auto", minWidth: "220px" }}
            >
              <option value="">Choose target author style</option>
              {authors.map((a) => (
                <option key={a} value={a}>
                  {a}
                </option>
              ))}
            </select>
          </div>

          <textarea
            className="textarea"
            placeholder="Paste your paragraph here (English or Nepali)…"
            value={text}
            onChange={(e) => setText(e.target.value)}
            style={{
              flex: 1,
              minHeight: 350,
              fontFamily: "monospace",
              fontSize: "1.05rem",
              resize: "none",
            }}
          />

          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <button
              className="btn primary"
              onClick={handleRewrite}
              disabled={loading || !text.trim() || !author}
              style={{ padding: "12px 32px" }}
            >
              {loading ? "Rewriting..." : "✨ Rewrite"}
            </button>
          </div>
        </div>

        <div className="panel" style={{ display: "flex", flexDirection: "column" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
            <h2 style={{ marginBottom: 16 }}>Output</h2>
            {lang ? (
              <span className="small" style={{ color: "var(--muted)" }}>
                Detected: <strong>{lang.toUpperCase()}</strong>
              </span>
            ) : null}
          </div>

          <div
            style={{
              flex: 1,
              background: "var(--input-bg)",
              borderRadius: 10,
              border: "1px solid var(--input-border)",
              padding: "1rem",
              minHeight: 350,
              fontFamily: "Georgia, serif",
              fontSize: "1.15rem",
              lineHeight: "1.8",
              whiteSpace: "pre-wrap",
              overflowY: "auto",
            }}
          >
            {out ? (
              <span className="fade-in">{out}</span>
            ) : (
              <span style={{ color: "var(--text-secondary)", fontStyle: "italic" }}>
                The rewritten version will appear here...
              </span>
            )}
          </div>

          {out && !out.startsWith("❌") && (
            <div style={{ marginTop: 16, display: "flex", justifyContent: "flex-end" }}>
              <button className="btn ghost" onClick={() => navigator.clipboard.writeText(out)}>
                📋 Copy
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
