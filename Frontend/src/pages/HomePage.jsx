import { useState } from "react";
import { useAuth } from "../context/AuthContext";

export default function HomePage() {
  const { user } = useAuth();
  const [text, setText] = useState("");
  const [author, setAuthor] = useState("");
  const [loading, setLoading] = useState(false);
  const [out, setOut] = useState("");

  // Placeholder – replace with your API call later
  async function handleRewrite() {
    if (!text.trim() || !author) return alert("Enter text and choose an author.");
    setLoading(true);
    setTimeout(() => {
      setOut(`🔧 [Demo] Rewritten in the style of ${author}:\n\n${text}\n\n— (Integrate /rewrite API here)`);
      setLoading(false);
    }, 850);
  }

  return (
    <div className="container" style={{ marginTop: 40, marginBottom: 60, maxWidth: "1200px" }}>
      <div style={{ marginBottom: 32, textAlign: "center" }}>
        <h1 style={{ marginBottom: 8 }}>Welcome back, {user?.name || "Writer"}! ✍️</h1>
        <p className="small" style={{ fontSize: "16px", color: "var(--muted)" }}>
          Transform your writing with AI-powered analysis and author-style rewriting
        </p>
      </div>

      <div className="grid grid-2" style={{ gap: 24 }}>
        <div className="panel fade-in">
          <h2 style={{ marginBottom: 16, fontSize: "24px" }}>Input</h2>
          <div style={{ marginBottom: 20 }}>
            <label className="small" style={{ marginBottom: 10, display: "block" }}>
              Your Text
            </label>
            <textarea
              className="textarea"
              placeholder="Paste your paragraph or text here to analyze and rewrite…"
              value={text}
              onChange={(e) => setText(e.target.value)}
              style={{ minHeight: "280px" }}
            />
          </div>

          <div style={{ marginBottom: 20 }}>
            <label className="small" style={{ marginBottom: 10, display: "block" }}>
              Target Author Style
            </label>
            <select 
              className="select" 
              value={author} 
              onChange={(e) => setAuthor(e.target.value)}
              style={{ marginBottom: 16 }}
            >
              <option value="">Choose target author style</option>
              <option>Franz Kafka</option>
              <option>Virginia Woolf</option>
              <option>George Orwell</option>
            </select>
          </div>

          <button 
            className="btn primary" 
            onClick={handleRewrite} 
            disabled={loading || !text.trim() || !author}
            style={{ width: "100%", padding: "14px 20px" }}
          >
            {loading ? "⏳ Analyzing & Rewriting…" : "🚀 Analyze & Rewrite"}
          </button>

          <div className="small" style={{ marginTop: 16, padding: "12px", background: "var(--primary-light)", borderRadius: "8px", border: "1px solid var(--border)" }}>
            <strong>Note:</strong> This is a demo placeholder. Integration with FastAPI <code>/rewrite</code> endpoint will provide real-time analysis and metrics.
          </div>
        </div>

        <div className="panel fade-in">
          <h2 style={{ marginBottom: 16, fontSize: "24px" }}>Output</h2>
          <div className="output-area">
            {out ? (
              <div style={{ whiteSpace: "pre-wrap", wordWrap: "break-word", lineHeight: "1.7" }}>
                {out}
              </div>
            ) : (
              <div style={{ color: "var(--muted)", fontStyle: "italic", textAlign: "center", paddingTop: "40px", fontFamily: "inherit" }}>
                Your rewritten text and analysis will appear here…
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
