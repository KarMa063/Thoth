const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

async function parseResponse(res, fallbackMessage) {
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data?.detail || fallbackMessage);
  }
  return data;
}

export async function getAuthors() {
  const res = await fetch(`${API_BASE}/authors`);
  const data = await parseResponse(res, "Failed to load authors");
  return data.authors || [];
}

export async function reloadAuthors() {
  const res = await fetch(`${API_BASE}/authors/reload`, { method: "POST" });
  const data = await parseResponse(res, "Failed to reload authors");
  return data.authors || [];
}

export async function addAuthorSample({ author, files }) {
  const formData = new FormData();
  formData.append("author", author);
  files.forEach((file) => formData.append("files", file));

  const res = await fetch(`${API_BASE}/authors`, {
    method: "POST",
    body: formData,
  });
  return parseResponse(res, "Failed to add author sample");
}

export async function rewriteText({ text, author, signal }) {
  const res = await fetch(`${API_BASE}/rewrite`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, author }),
    signal,
  });
  return parseResponse(res, "Rewrite failed");
}

export async function continueText({ text, author, signal }) {
  const res = await fetch(`${API_BASE}/continue`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, author }),
    signal,
  });
  return parseResponse(res, "Continuation failed");
}

export async function analyzeText({ text, signal }) {
  const res = await fetch(`${API_BASE}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
    signal,
  });
  return parseResponse(res, "Analysis failed");
}
