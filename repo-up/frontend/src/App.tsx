import { useState } from "react";
import { Landing } from "./components/Landing";
import { Progress } from "./components/Progress";
import { Results } from "./components/Results";
import { DependencyGraphBackground } from "./components/DependencyGraphBackground";
import { Code2 } from "lucide-react";
import { FileGraph } from "./components/FileGraph";

import { SandboxVerification } from "./components/sandbox/SandboxVerification";

/** Centralised backend URL — override via VITE_API_URL env var. */
export const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

type Screen = "landing" | "progress" | "graph-reveal" | "results" | "sandbox";

function App() {
  const [currentScreen, setCurrentScreen] = useState<Screen>("landing");
  const [analysisData, setAnalysisData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const showError = (msg: string) => {
    setError(msg);
    setTimeout(() => setError(null), 5000);
  };

  const handleAnalyze = async (file?: File) => {
    if (!file) {
      showError("Please select a ZIP file first.");
      return;
    }

    if (!file.name.toLowerCase().endsWith(".zip")) {
      showError(
        "Only .zip files are supported. Please select a valid ZIP archive.",
      );
      return;
    }

    setCurrentScreen("progress");
    setError(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      setAnalysisData({ graph: { nodes: [], edges: [] } });

      const res = await fetch(`${API_BASE}/analyze`, {
        method: "POST",
        body: formData,
      });

      setCurrentScreen("graph-reveal");

      if (!res.ok) {
        let msg = "Analysis failed.";
        try {
          const errData = await res.json();
          // Support both {"error":{"message":"..."}} and legacy {"detail":"..."}
          msg = errData?.error?.message ?? errData?.detail ?? msg;
        } catch (_) {
          /* ignore parse errors */
        }
        throw new Error(msg);
      }

      const reader = res.body!.getReader();
      const decoder = new TextDecoder("utf-8");

      const liveNodes: { id: string; label: string }[] = [];
      const liveEdges: { source: string; target: string }[] = [];

      let buffer = "";
      let receivedDone = false;

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const dataStr = line.replace("data: ", "");
            try {
              const event = JSON.parse(dataStr);
              if (event.type === "file") {
                liveNodes.push({
                  id: event.path,
                  label:
                    event.path.replace(/\\/g, "/").split("/").pop() ??
                    event.path,
                });
                setAnalysisData((prev: any) => ({
                  ...prev,
                  graph: { nodes: [...liveNodes], edges: [...liveEdges] },
                }));
              } else if (event.type === "edge") {
                liveEdges.push({ source: event.source, target: event.target });
                setAnalysisData((prev: any) => ({
                  ...prev,
                  graph: { nodes: [...liveNodes], edges: [...liveEdges] },
                }));
              } else if (event.type === "done") {
                receivedDone = true;
                setAnalysisData(event.result);
                setTimeout(() => setCurrentScreen("results"), 1000);
              } else if (event.type === "error") {
                // Backend emitted a stream-level error event
                const streamMsg =
                  event.error?.message ?? "Analysis encountered an error.";
                throw new Error(streamMsg);
              }
            } catch (e) {
              if (
                e instanceof Error &&
                e.message !== "Failed to parse SSE line"
              )
                throw e;
              console.error("Failed to parse SSE line", e);
            }
          }
        }
      }

      // If stream ended without a "done" event, go back to landing with error
      if (!receivedDone) {
        throw new Error(
          "Analysis did not complete — the connection ended unexpectedly. Please try again.",
        );
      }
    } catch (err: any) {
      showError(err.message ?? "Failed to connect to the backend.");
      setCurrentScreen("landing");
    }
  };

  return (
    <div className="h-screen flex flex-col font-sans bg-[#05050A] text-primary-dark selection:bg-primary-brand/30 selection:text-primary-brand relative overflow-hidden">
      {/* Toast Error */}
      {error && (
        <div className="absolute top-6 left-1/2 -translate-x-1/2 z-50 bg-[#FF5F56]/10 border border-[#FF5F56]/50 text-[#FF5F56] px-6 py-3 rounded-lg shadow-2xl flex items-center gap-3 backdrop-blur-md font-medium text-sm">
          <div className="w-2 h-2 rounded-full bg-[#FF5F56] shadow-[0_0_8px_rgba(255,95,86,0.8)]" />
          {error}
        </div>
      )}

      {/* Animated Dependency Graph Background */}
      <div
        className={`absolute inset-0 z-0 transition-opacity duration-1000 pointer-events-none ${currentScreen === "results" ? "opacity-15" : "opacity-100"}`}
      >
        <DependencyGraphBackground />
      </div>

      {/* Global Header */}
      {currentScreen !== "results" && (
        <header className="w-full py-6 px-8 flex items-center justify-between relative z-20">
          <div
            className="flex items-center gap-3 cursor-pointer"
            onClick={() => setCurrentScreen("landing")}
          >
            <div className="w-9 h-9 rounded-full bg-[#13151A] border border-[#6D5EF0]/30 flex items-center justify-center text-primary-brand shadow-[0_0_15px_rgba(109,94,240,0.15)]">
              <Code2 size={18} />
            </div>
            {currentScreen !== "landing" && (
              <span className="font-bold text-lg tracking-tight text-white">
                Repo-Up
              </span>
            )}
          </div>
        </header>
      )}

      {/* Main Content Area */}
      <main
        className={`flex-1 min-h-0 overflow-hidden flex flex-col relative z-10 w-full ${currentScreen === "landing" ? "items-center justify-start pt-24 lg:pt-32" : currentScreen !== "results" ? "items-center justify-center" : ""}`}
      >
        {currentScreen === "landing" && <Landing onAnalyze={handleAnalyze} />}

        {currentScreen === "progress" && <Progress />}

        {currentScreen === "graph-reveal" && (
          <div className="w-full max-w-5xl h-[70vh] min-h-[500px] p-8 flex flex-col items-center justify-center relative z-20">
            <h2 className="text-2xl font-bold text-white mb-6 animate-pulse">
              Mapping Codebase Architecture...
            </h2>
            {analysisData?.graph ? (
              <FileGraph
                mode="streaming"
                nodes={analysisData.graph.nodes}
                edges={analysisData.graph.edges}
              />
            ) : (
              <div className="text-red-500">
                Failed to load graph data.
                <button
                  className="ml-4 underline"
                  onClick={() => setCurrentScreen("results")}
                >
                  Continue
                </button>
              </div>
            )}
          </div>
        )}

        {currentScreen === "results" && (
          <Results
            data={analysisData}
            onReset={() => {
              setCurrentScreen("landing");
              setAnalysisData(null);
            }}
            onApplyAll={() => {
              setCurrentScreen("sandbox");
            }}
          />
        )}

        {currentScreen === "sandbox" && (
          <SandboxVerification
            sessionId={analysisData?.session_id}
            findings={analysisData?.issues ?? []}
            onClose={(updatedData?: any) => {
              if (updatedData && typeof updatedData === "object") {
                setAnalysisData((prev: any) => {
                  if (!prev) return prev;
                  const newState = { ...prev, ...updatedData };

                  if (updatedData.scoreBump && prev.rubric) {
                    const bump = updatedData.scoreBump;
                    newState.score = Math.min(
                      100,
                      (prev.score ?? 0) + bump.total,
                    );
                    newState.rubric = {
                      ...prev.rubric,
                      final_score: Math.min(
                        100,
                        (prev.rubric.final_score ?? 0) + bump.total,
                      ),
                      security_score: Math.min(
                        100,
                        (prev.rubric.security_score ?? 0) + bump.security,
                      ),
                      structural_score: Math.min(
                        100,
                        (prev.rubric.structural_score ?? 0) + bump.structural,
                      ),
                    };
                  }
                  return newState;
                });
              }
              setCurrentScreen("results");
            }}
          />
        )}
      </main>
    </div>
  );
}

export default App;
