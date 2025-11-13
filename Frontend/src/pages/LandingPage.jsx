import { Link } from "react-router-dom";

export default function LandingPage() {
  return (
    <>
      <section className="hero center">
        <div className="container center" style={{ textAlign: "center", gap: 24, maxWidth: "900px" }}>
          <h1>Thoth — Bilingual Psycho-Literary Assistant</h1>
          <p className="lead">
            Analyze writing, detect biases, and rewrite in the voice of renowned authors.
            Start with English; Nepali support coming next. Clean UI with explainable insights.
          </p>
          <div style={{ display: "flex", gap: 16, marginTop: 8, flexWrap: "wrap", justifyContent: "center" }}>
            <Link to="/login" className="btn primary">Get Started</Link>
            <a href="#features" className="btn ghost">Learn More</a>
          </div>
        </div>
      </section>

      <section id="features" className="container">
        <div style={{ textAlign: "center", marginBottom: 48 }}>
          <h2 style={{ marginBottom: 12 }}>Key Features</h2>
          <p className="small" style={{ fontSize: "16px", maxWidth: "600px", margin: "0 auto" }}>
            Powerful tools to enhance your writing and understand your style
          </p>
        </div>
        <div className="features">
          {[
            { 
              title: "Author Tone", 
              desc: "Rewriting guided by exemplar-based style sheets. Transform your writing to match the voice of renowned authors.",
              icon: "✍️"
            },
            { 
              title: "Bias & Strengths", 
              desc: "Surface hedging, clarity, rhythm, and vocabulary richness. Get insights into your writing patterns.",
              icon: "🔍"
            },
            { 
              title: "Explainability", 
              desc: "Show 'why': tone tags, anchors, and style stats. Understand the reasoning behind every suggestion.",
              icon: "💡"
            },
          ].map((f, i) => (
            <div key={i} className="panel feature fade-in" style={{ animationDelay: `${i * 0.1}s` }}>
              <div style={{ fontSize: "32px", marginBottom: "12px" }}>{f.icon}</div>
              <h3>{f.title}</h3>
              <p className="small" style={{ margin: 0 }}>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <footer>© {new Date().getFullYear()} Thoth. All rights reserved.</footer>
    </>
  );
}
