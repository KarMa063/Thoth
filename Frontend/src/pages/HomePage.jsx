import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import DashboardTabs from "../components/dashboard/DashboardTabs";
import EditorPanel from "../components/dashboard/EditorPanel";
import OutputPanel from "../components/dashboard/OutputPanel";
import { MICROCOPY, PIPELINE_STEPS, TAB_META } from "../constants/dashboard";
import { useAuth } from "../context/AuthContext";
import { analyzeText, continueText, getAuthors, rewriteText } from "../services/api";
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
      </header>

      {authorError && (
        <div className="error-inline">
          Start the backend server, then refresh to load the author corpus.
        </div>
      )}

      <DashboardTabs activeTab={activeTab} onChange={handleTabChange} />

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
