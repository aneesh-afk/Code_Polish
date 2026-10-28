import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { X, FileCode } from 'lucide-react';
import Editor from '@monaco-editor/react';
import { API_BASE } from '../App';

/** Maximum bytes loaded into the editor to avoid freezing on huge files. */
const MAX_CONTENT_BYTES = 500_000;

interface Finding {
  category: string;
  title: string;
  description: string;
  severity: 'High' | 'Medium' | 'Low';
  file?: string;
  line?: number;
}

interface CodeViewerProps {
  sessionId: string;
  filePath: string;
  line?: number;
  fileIssues?: Finding[];
  onClose: () => void;
}

export const CodeViewer: React.FC<CodeViewerProps> = ({ sessionId, filePath, line, fileIssues = [], onClose }) => {
  const [content, setContent] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [editorInstance, setEditorInstance] = useState<any>(null);
  const [monacoInstance, setMonacoInstance] = useState<any>(null);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);
    setContent(null);

    fetch(`${API_BASE}/file-content?session_id=${encodeURIComponent(sessionId)}&path=${encodeURIComponent(filePath)}`)
      .then(res => {
        if (!res.ok) {
          return res.json().then(errData => {
            const msg = errData?.error?.message ?? errData?.detail ?? 'Could not load file.';
            throw new Error(msg);
          });
        }
        return res.json();
      })
      .then(data => {
        if (isMounted) {
          let text: string = data.content ?? '';
          // Guard against monster files
          if (text.length > MAX_CONTENT_BYTES) {
            text = text.slice(0, MAX_CONTENT_BYTES) + '\n\n[… file truncated for display …]';
          }
          setContent(text);
          setLoading(false);
        }
      })
      .catch(err => {
        if (isMounted) {
          const msg: string = err?.message ?? 'Could not load file content.';
          // Surface session-expired errors with a friendlier message
          if (msg.toLowerCase().includes('session')) {
            setError('Session expired — please re-analyse the project to view source files.');
          } else if (msg.toLowerCase().includes('not found')) {
            setError('File not found in this session. It may have been generated or excluded from the archive.');
          } else {
            setError(msg);
          }
          setLoading(false);
        }
      });

    return () => { isMounted = false; };
  }, [sessionId, filePath]);

  useEffect(() => {
    if (editorInstance && line) {
      editorInstance.revealLineInCenter(line);
    }
  }, [editorInstance, line]);

  useEffect(() => {
    if (editorInstance && monacoInstance && fileIssues.length > 0) {
      const model = editorInstance.getModel();
      if (!model) return;

      const markers = fileIssues
        .filter(i => i.line)
        .map(issue => {
          let severityLevel = monacoInstance.MarkerSeverity.Info;
          if (issue.severity === 'High') severityLevel = monacoInstance.MarkerSeverity.Error;
          else if (issue.severity === 'Medium') severityLevel = monacoInstance.MarkerSeverity.Warning;

          return {
            startLineNumber: issue.line!,
            startColumn: 1,
            endLineNumber: issue.line!,
            endColumn: 1000,
            message: `${issue.title}\n\n${issue.description}`,
            severity: severityLevel,
            source: 'Repo-Up',
          };
        });

      monacoInstance.editor.setModelMarkers(model, 'repo-up', markers);
    }
  }, [editorInstance, monacoInstance, fileIssues]);

  const handleEditorDidMount = (editor: any, monaco: any) => {
    setEditorInstance(editor);
    setMonacoInstance(monaco);
    if (line) {
      editor.revealLineInCenter(line);
    }
  };

  const getLanguage = (path: string): string => {
    const ext = path.split('.').pop()?.toLowerCase() ?? '';
    switch (ext) {
      case 'ts': case 'tsx': return 'typescript';
      case 'js': case 'jsx': return 'javascript';
      case 'py': return 'python';
      case 'java': return 'java';
      case 'cpp': case 'cc': case 'cxx': case 'h': case 'hpp': return 'cpp';
      case 'json': return 'json';
      case 'html': return 'html';
      case 'css': return 'css';
      case 'md': return 'markdown';
      default: return 'plaintext';
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="absolute inset-0 z-40 bg-black/60 backdrop-blur-sm flex items-center justify-center p-8"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <motion.div
        initial={{ y: 20, opacity: 0, scale: 0.95 }}
        animate={{ y: 0, opacity: 1, scale: 1 }}
        exit={{ y: 20, opacity: 0, scale: 0.95 }}
        className="w-full max-w-5xl h-full max-h-[85vh] bg-[#0B0C10] border border-white/10 rounded-2xl shadow-2xl flex flex-col overflow-hidden relative"
      >
        {/* Header */}
        <div className="h-14 border-b border-white/10 bg-white/5 flex items-center justify-between px-6 shrink-0">
          <div className="flex items-center gap-3 min-w-0">
            <FileCode size={18} className="text-[#6D5EF0] shrink-0" />
            <span className="font-mono text-sm text-white font-medium truncate">{filePath}</span>
            {line && (
              <span className="bg-white/10 text-gray-300 px-2 py-0.5 rounded text-xs font-mono shrink-0">
                Line {line}
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-1.5 hover:bg-white/10 rounded-lg text-gray-400 hover:text-white transition-colors shrink-0"
            aria-label="Close code viewer"
          >
            <X size={18} />
          </button>
        </div>

        {/* Editor Area */}
        <div className="flex-1 relative bg-[#05050A]">
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center text-gray-400 text-sm">
              <div className="animate-pulse flex items-center gap-2">
                Loading source code…
              </div>
            </div>
          )}

          {error && (
            <div className="absolute inset-0 flex flex-col items-center justify-center text-gray-400 text-sm p-10 text-center gap-4">
              <FileCode size={40} className="text-gray-600" />
              <p className="max-w-md leading-relaxed">{error}</p>
              <button
                onClick={onClose}
                className="mt-2 px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-gray-300 hover:text-white hover:bg-white/10 transition-colors"
              >
                Close
              </button>
            </div>
          )}

          {!loading && !error && content !== null && (
            <Editor
              height="100%"
              language={getLanguage(filePath)}
              theme="vs-dark"
              value={content}
              onMount={handleEditorDidMount}
              options={{
                readOnly: true,
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                fontSize: 13,
                fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                lineHeight: 24,
                padding: { top: 24, bottom: 24 },
                renderLineHighlight: 'none',
                scrollbar: {
                  useShadows: false,
                  verticalScrollbarSize: 10,
                  horizontalScrollbarSize: 10,
                },
              }}
            />
          )}
        </div>
      </motion.div>
    </motion.div>
  );
};
