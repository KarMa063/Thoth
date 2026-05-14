import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import DashboardTabs from "../components/dashboard/DashboardTabs";
import EditorPanel from "../components/dashboard/EditorPanel";
import OutputPanel from "../components/dashboard/OutputPanel";
import { MICROCOPY, PIPELINE_STEPS, TAB_META } from "../constants/dashboard";
import { useAuth } from "../context/AuthContext";
import { addAuthorSample, analyzeText, continueText, getAuthors, reloadAuthors, rewriteText } from "../services/api";
import { formatAnalysisReport } from "../utils/analysisFormatter";

export default function HomePage() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState("rewrite");
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [out, setOut] = useState("");
  const [author, setAuthor] = useState("");
  const [authors, setAuthors] = useState([]);
  const [authorError, setAuthorError] = useState("");
  const [lang, setLang] = useState("");
  const [toast, setToast] = useState("");
  const [newAuthor, setNewAuthor] = useState("");
  const [authorFiles, setAuthorFiles] = useState([]);
  const [savingAuthor, setSavingAuthor] = useState(false);
  const [sampleError, setSampleError] = useState("");
  const [currentStep, setCurrentStep] = useState(0);
  const [microcopyIndex, setMicrocopyIndex] = useState(0);
  const [elapsedTime, setElapsedTime] = useState(0);

  const abortControllerRef = useRef(null);
  const stepIntervalRef = useRef(null);
  const microcopyIntervalRef = useRef(null);
  const timerIntervalRef = useRef(null);
  const toastTimeoutRef = useRef(null);

  const clearDashboardTimers = useCallback(() => {
    clearInterval(stepIntervalRef.current);
    clearInterval(microcopyIntervalRef.current);
    clearInterval(timerIntervalRef.current);
  }, []);

  useEffect(() => {
    let ignore = false;

    async function loadAuthors() {
      try {
        const authorList = await getAuthors();
        if (!ignore) {
          setAuthors(authorList);
          setAuthorError("");
        }
      } catch (error) {
        if (!ignore) {
          setAuthors([]);
          setAuthorError(error.message || "Author list unavailable");
        }
      }
    }

    loadAuthors();
    return () => {
      ignore = true;
    };
  }, []);

  useEffect(() => {
    if (!loading) {
      setCurrentStep(PIPELINE_STEPS[activeTab].length - 1);
      clearDashboardTimers();
      return undefined;
    }

    const steps = PIPELINE_STEPS[activeTab];
    let step = 0;
    setCurrentStep(0);
    setMicrocopyIndex(0);
    setElapsedTime(0);

    stepIntervalRef.current = setInterval(() => {
      step += 1;
      if (step < steps.length - 1) setCurrentStep(step);
    }, 2500);

    microcopyIntervalRef.current = setInterval(() => {
      setMicrocopyIndex((prev) => (prev + 1) % MICROCOPY[activeTab].length);
    }, 2800);

    timerIntervalRef.current = setInterval(() => {
      setElapsedTime((prev) => prev + 1);
    }, 1000);

    return clearDashboardTimers;
  }, [loading, activeTab, clearDashboardTimers]);

  useEffect(() => {
    return () => {
      clearDashboardTimers();
      clearTimeout(toastTimeoutRef.current);
      abortControllerRef.current?.abort();
    };
  }, [clearDashboardTimers]);

  const { wordCount, charCount } = useMemo(() => ({
    wordCount: text.trim() ? text.trim().split(/\s+/).length : 0,
    charCount: text.length,
  }), [text]);

  const showToast = useCallback((message) => {
    clearTimeout(toastTimeoutRef.current);
    setToast(message);
    toastTimeoutRef.current = setTimeout(() => setToast(""), 2000);
  }, []);

  const handleCancel = useCallback(() => {
    abortControllerRef.current?.abort();
    setLoading(false);
    setOut("Generation cancelled. You can try again or switch modes.");
  }, []);

  const runRequest = useCallback(async (request) => {
    const controller = new AbortController();
    abortControllerRef.current = controller;
    setLoading(true);
    setOut("");
    setLang("");

    try {
      await request(controller.signal);
    } catch (error) {
      if (error.name !== "AbortError") {
        setOut(error.message);
      }
    } finally {
      setLoading(false);
      abortControllerRef.current = null;
    }
  }, []);

  const handleRewrite = useCallback(() => {
    if (!text.trim() || !author) return;
    runRequest(async (signal) => {
      const data = await rewriteText({ text, author, signal });
      setOut(data.rewritten || "");
      setLang(data.language || "");
    });
  }, [author, runRequest, text]);

  const handleContinue = useCallback(() => {
    if (!text.trim() || !author) return;
    runRequest(async (signal) => {
      const data = await continueText({ text, author, signal });
      setOut(data.continuation || "");
    });
  }, [author, runRequest, text]);

  const handleAnalyze = useCallback(() => {
    if (!text.trim()) return;
    runRequest(async (signal) => {
      const data = await analyzeText({ text, signal });
      setOut(formatAnalysisReport(data));
    });
  }, [runRequest, text]);

  const handleAction = useCallback(() => {
    if (activeTab === "rewrite") handleRewrite();
    else if (activeTab === "continue") handleContinue();
    else handleAnalyze();
  }, [activeTab, handleAnalyze, handleContinue, handleRewrite]);

  const handleTabChange = useCallback((tab) => {
    if (loading) return;
    setActiveTab(tab);
    setOut("");
    setLang("");
  }, [loading]);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(out);
      showToast("Copied to clipboard");
    } catch {
      showToast("Copy unavailable");
    }
  }, [out, showToast]);

  const handleAddAuthor = useCallback(async (event) => {
    event.preventDefault();
    const trimmedAuthor = newAuthor.trim();
    if (!trimmedAuthor || authorFiles.length === 0 || savingAuthor) return;

    setSavingAuthor(true);
    setSampleError("");

    try {
      const data = await addAuthorSample({ author: trimmedAuthor, files: authorFiles });
      const nextAuthors = data.authors || await getAuthors();
      setAuthors(nextAuthors);
      setAuthor(data.author || trimmedAuthor);
      setNewAuthor("");
      setAuthorFiles([]);
      setAuthorError("");
      showToast(`Author style added from ${data.files_processed} file(s)`);
    } catch (error) {
      setSampleError(error.message || "Could not add author style");
    } finally {
      setSavingAuthor(false);
    }
  }, [authorFiles, newAuthor, savingAuthor, showToast]);

  const handleReloadAuthors = useCallback(async () => {
    try {
      const authorList = await reloadAuthors();
      setAuthors(authorList);
      if (author && !authorList.includes(author)) {
        setAuthor("");
      }
      setAuthorError("");
      showToast("Authors reloaded");
    } catch (error) {
      setAuthorError(error.message || "Author reload failed");
    }
  }, [author, showToast]);

  const authorStatus = authorError
    ? "Author list unavailable"
    : authors.length > 0
      ? `${authors.length} authors available`
      : "Loading corpus...";

  return (
    <div className="workspace">
      <header className="workspace-topbar">
        <div>
          <h1>
            Welcome back, <span className="gradient-text">{user?.name || "Writer"}</span>
          </h1>
          <p>{TAB_META[activeTab].desc}</p>
        </div>
        <span className={`workspace-status ${authorError ? "error" : ""}`}>
          {authorStatus}
        </span>
        <button className="btn ghost btn-compact" type="button" onClick={handleReloadAuthors}>
          Reload authors
        </button>
      </header>

      {authorError && (
        <div className="error-inline">
          Start the backend server, then refresh to load the author corpus.
        </div>
      )}

      <DashboardTabs activeTab={activeTab} onChange={handleTabChange} />

      <form className="author-sample-panel" onSubmit={handleAddAuthor}>
        <div className="author-sample-header">
          <div>
            <span className="panel-label">Custom Author</span>
            <h2>Add an author style</h2>
          </div>
          <button
            className="btn primary btn-compact"
            type="submit"
            disabled={savingAuthor || !newAuthor.trim() || authorFiles.length === 0}
          >
            {savingAuthor ? "Checking..." : "Upload author"}
          </button>
        </div>
        <div className="author-sample-grid">
          <input
            className="input"
            value={newAuthor}
            onChange={(event) => setNewAuthor(event.target.value)}
            placeholder="Author name"
            disabled={savingAuthor}
          />
          <label className="author-file-input">
            <input
              key={authorFiles.map((file) => file.name).join("|") || "empty-files"}
              type="file"
              accept=".txt,.docx,text/plain,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              multiple
              onChange={(event) => setAuthorFiles(Array.from(event.target.files || []))}
              disabled={savingAuthor}
            />
            <span>
              {authorFiles.length > 0
                ? `${authorFiles.length} file(s) selected`
                : "Choose text or DOCX files"}
            </span>
          </label>
        </div>
        <p className="author-sample-note">
          Upload a .txt or .docx file. The backend cleans it and saves it only when the cleaned text reaches 300 words.
        </p>
        {sampleError && (
          <div className="error-inline" role="alert">
            {sampleError}
          </div>
        )}
      </form>

      <div className="editor-layout">
        <EditorPanel
          activeTab={activeTab}
          author={author}
          authors={authors}
          charCount={charCount}
          lang={lang}
          loading={loading}
          onAction={handleAction}
          onAuthorChange={setAuthor}
          onCancel={handleCancel}
          onTextChange={setText}
          text={text}
          wordCount={wordCount}
        />

        <OutputPanel
          activeTab={activeTab}
          author={author}
          currentStep={currentStep}
          elapsedTime={elapsedTime}
          lang={lang}
          loading={loading}
          microcopyIndex={microcopyIndex}
          onClear={() => setOut("")}
          onCopy={handleCopy}
          out={out}
          wordCount={wordCount}
        />
      </div>

      <div className={`toast ${toast ? "visible" : ""}`}>{toast}</div>
    </div>
  );
}
