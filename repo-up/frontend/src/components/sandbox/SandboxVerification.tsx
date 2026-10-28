import React, { useEffect, useState, useRef } from 'react';
import { Network, CheckCircle2, AlertCircle, XCircle, Pause, Play, Square, Activity, Code2 } from 'lucide-react';
import { FileGraph } from '../FileGraph';
import { API_BASE } from '../../App';
import { DependencyGraphBackground } from '../DependencyGraphBackground';

interface Finding {
  rule_id?: string;
  category: string;
  title: string;
  description: string;
  severity: string;
  file?: string;
  line?: number;
  autofix_available?: boolean;
}

interface SandboxProps {
  sessionId: string;
  findings: Finding[];
  onClose: (updatedData?: any) => void;
}

type SSEState = 'idle' | 'connecting' | 'active' | 'reconnecting' | 'disconnected' | 'completed' | 'paused';
type FixStatus = 'queued' | 'running' | 'passed' | 'failed' | 'conflict' | 'blocked';

interface QueueItem {
  finding: Finding;
  status: FixStatus;
  message?: string;
  patch?: any;
  durationMs?: number;
}

export const SandboxVerification: React.FC<SandboxProps> = ({ sessionId, findings, onClose }) => {
  const autofixFindings = findings.filter(f => f.autofix_available);
  
  const [sseState, setSseState] = useState<SSEState>('connecting');
  const [queue, setQueue] = useState<QueueItem[]>(autofixFindings.map(f => ({ finding: f, status: 'queued' })));
  const [activeIdx, setActiveIdx] = useState<number | null>(null);
  
  const [graphNodes, setGraphNodes] = useState<{ id: string; label: string; state?: string }[]>([]);
  const [graphEdges, setGraphEdges] = useState<{ source: string; target: string }[]>([]);
  
  const [pipelineState, setPipelineState] = useState<Record<string, string>>({});
  
  const abortController = useRef<AbortController | null>(null);

  useEffect(() => {
    if (autofixFindings.length === 0) {
      setSseState('completed');
      return;
    }
    startRun();
    return () => {
      if (abortController.current) abortController.current.abort();
    };
  }, []);

  const startRun = async () => {
    setSseState('active');
    abortController.current = new AbortController();
    
    try {
      const res = await fetch(`${API_BASE}/sandbox/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, findings: autofixFindings }),
        signal: abortController.current.signal,
      });

      if (!res.ok) {
        setSseState('disconnected');
        return;
      }

      const reader = res.body!.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.replace('data: ', '');
            try {
              const event = JSON.parse(dataStr);
              handleEvent(event);
            } catch (e) {
              console.error('Failed to parse SSE', e);
            }
          }
        }
      }
    } catch (err: any) {
      if (err.name === 'AbortError') return;
      setSseState('disconnected');
    }
  };

  const handleEvent = (event: any) => {
    switch (event.type) {
      case 'graph_updated':
        if (event.graph) {
          setGraphNodes(event.graph.nodes);
          setGraphEdges(event.graph.edges);
        }
        break;
      case 'fix_started':
        setActiveIdx(event.fix_idx);
        updateQueue(event.fix_idx, 'running');
        setPipelineState({ patch: 'running' });
        highlightNode(event.finding.file);
        break;
      case 'patch_applied':
        setPipelineState(p => ({ ...p, patch: 'passed', parse: 'running' }));
        updateQueue(event.fix_idx, 'running', undefined, event.patch);
        break;
      case 'parse_completed':
        setPipelineState(p => ({ ...p, parse: 'passed', analysis: 'running' }));
        break;
      case 'analysis_completed':
        setPipelineState(p => ({ ...p, analysis: 'passed', security: 'running' }));
        break;
      case 'security_check':
        setPipelineState(p => ({ ...p, security: 'passed', test: 'running' }));
        break;
      case 'test_completed':
        setPipelineState(p => ({ ...p, test: (event.test_status === 'PASS' || event.test_status === 'NOT_AVAILABLE') ? 'passed' : 'failed' }));
        break;
      case 'fix_passed':
        updateQueue(event.fix_idx, 'passed', 'Verified successfully');
        break;
      case 'fix_failed':
      case 'regression_detected':
        updateQueue(event.fix_idx, 'failed', event.message);
        break;
      case 'fix_blocked':
        updateQueue(event.fix_idx, 'blocked', event.message);
        break;
      case 'sandbox_completed':
        setSseState('completed');
        setActiveIdx(null);
        break;
      case 'error':
        setSseState('disconnected');
        break;
    }
  };

  const updateQueue = (idx: number, status: FixStatus, msg?: string, patch?: any) => {
    setQueue(q => {
      const n = [...q];
      n[idx] = { ...n[idx], status, message: msg || n[idx].message, patch: patch || n[idx].patch };
      return n;
    });
  };

  const highlightNode = (file?: string) => {
    if (!file) return;
    setGraphNodes(nodes => nodes.map(n => {
      if (file.includes(n.label)) return { ...n, state: 'active' };
      return { ...n, state: 'idle' };
    }));
  };

  const handleClose = () => {
    const passedFindingsList = queue.filter(q => q.status === 'passed').map(q => q.finding);
    const passedFindings = new Set(passedFindingsList);
    const updatedIssues = findings.filter(f => !passedFindings.has(f));
    
    let scoreBump = 0;
    let securityBump = 0;
    let structuralBump = 0;

    passedFindingsList.forEach(f => {
       const weight = f.severity?.toLowerCase() === 'high' ? 5 : f.severity?.toLowerCase() === 'medium' ? 3 : 1;
       scoreBump += weight;
       if (f.category?.toLowerCase().includes('security')) {
           securityBump += weight * 2;
       } else {
           structuralBump += weight * 1.5;
       }
    });

    onClose({
      issues: updatedIssues,
      graph: { nodes: graphNodes, edges: graphEdges },
      scoreBump: {
         total: Math.round(scoreBump),
         security: Math.round(securityBump),
         structural: Math.round(structuralBump)
      }
    });
  };

  const activeFix = activeIdx !== null ? queue[activeIdx] : null;

  return (
    <div className="flex h-screen w-full bg-[#05050A] text-white overflow-hidden font-sans relative">
      <div className="absolute inset-0 z-0 pointer-events-none opacity-[0.05]">
        <DependencyGraphBackground />
      </div>

      <div className="flex-1 flex flex-col min-w-0 relative z-10 h-full">
        {/* HEADER */}
        <header className="h-16 border-b border-white/5 bg-[#05050A]/70 backdrop-blur-md flex items-center justify-between px-6 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-[#13151A] border border-[#6D5EF0]/30 flex items-center justify-center text-primary-brand shadow-[0_0_10px_rgba(109,94,240,0.2)]">
              <Code2 size={16} />
            </div>
            <div>
              <div className="font-bold text-sm tracking-tight">SANDBOX VERIFICATION</div>
              <div className="text-[10px] text-gray-500 font-mono">sbx_{sessionId.substring(0, 8)}</div>
            </div>
          </div>

          <div className="flex items-center gap-6">
            <div className={`flex items-center gap-2 px-3 py-1 rounded-full border text-xs font-medium
              ${sseState === 'active' ? 'bg-[#10B981]/10 border-[#10B981]/30 text-[#10B981]' : 
                sseState === 'completed' ? 'bg-[#3B82F6]/10 border-[#3B82F6]/30 text-[#3B82F6]' :
                sseState === 'connecting' ? 'bg-[#F59E0B]/10 border-[#F59E0B]/30 text-[#F59E0B]' :
                'bg-red-500/10 border-red-500/30 text-red-500'}`}
            >
              <div className={`w-2 h-2 rounded-full ${sseState === 'active' ? 'bg-[#10B981] animate-pulse' : sseState === 'completed' ? 'bg-[#3B82F6]' : 'bg-red-500'}`} />
              SSE Stream: {sseState.toUpperCase()}
            </div>
            
            <div className="flex items-center gap-3">
              <div className="text-xs font-bold">Progress: {queue.filter(q => q.status === 'passed').length} / {queue.length} fixes verified</div>
              <div className="w-32 h-1.5 bg-white/10 rounded-full overflow-hidden">
                <div className="h-full bg-gradient-to-r from-[#6D5EF0] to-[#3B82F6]" style={{ width: `${(queue.filter(q => q.status !== 'queued' && q.status !== 'running').length / queue.length) * 100}%` }} />
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button className="flex items-center gap-1.5 text-xs font-medium bg-white/5 hover:bg-white/10 border border-white/10 px-3 py-1.5 rounded-lg transition-colors" onClick={handleClose}>
              <Activity size={14} /> Preview Summary
            </button>
            <button className="flex items-center gap-1.5 text-xs font-medium bg-white/5 hover:bg-white/10 border border-white/10 px-3 py-1.5 rounded-lg transition-colors" onClick={handleClose}>
              <Square size={14} /> Stop Sandbox
            </button>
          </div>
        </header>

        {/* MAIN LAYOUT */}
        <div className="flex-1 flex min-h-0 overflow-hidden">
          {/* QUEUE */}
          <div className="w-80 border-r border-white/5 bg-black/40 flex flex-col">
            <div className="p-4 border-b border-white/5 flex items-center justify-between bg-white/5">
              <h3 className="font-bold text-sm text-gray-200 flex items-center gap-2"><CheckCircle2 size={14} className="text-[#6D5EF0]" /> VERIFICATION QUEUE</h3>
              <span className="text-xs bg-white/10 px-2 py-0.5 rounded-full">{queue.length} total</span>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {queue.map((item, i) => (
                <div key={i} className={`p-3 rounded-lg border transition-all ${item.status === 'running' ? 'bg-[#6D5EF0]/10 border-[#6D5EF0]/50 shadow-[0_0_15px_rgba(109,94,240,0.15)]' : 'bg-black/60 border-white/10'}`}>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2 text-xs font-bold">
                      {item.status === 'passed' && <CheckCircle2 size={12} className="text-[#10B981]" />}
                      {item.status === 'running' && <div className="w-2 h-2 rounded-full bg-[#3B82F6] animate-pulse" />}
                      {item.status === 'queued' && <div className="w-2 h-2 rounded-full bg-gray-500" />}
                      {(item.status === 'failed' || item.status === 'conflict' || item.status === 'blocked') && <AlertCircle size={12} className="text-red-400" />}
                      <span className="text-gray-300">FIX-{(i+1).toString().padStart(2, '0')}</span>
                    </div>
                    {item.status === 'running' && <span className="text-[10px] font-bold bg-[#6D5EF0]/20 text-[#8B5CF6] px-2 py-0.5 rounded uppercase">ACTIVE</span>}
                  </div>
                  <div className="text-[10px] text-gray-400 font-mono mb-1 truncate">{item.finding.file}:{item.finding.line}</div>
                  <div className="text-xs text-gray-300 line-clamp-2">{item.finding.title}</div>
                  {item.message && (
                    <div className={`mt-2 text-[10px] p-1.5 rounded border ${item.status === 'passed' ? 'bg-[#10B981]/10 border-[#10B981]/30 text-[#10B981]' : 'bg-red-400/10 border-red-400/30 text-red-400'}`}>
                      {item.message}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* GRAPH & DETAILS */}
          <div className="flex-1 flex flex-col min-w-0 bg-[#0B0C10]/40">
            {/* Graph */}
            <div className="flex-1 relative border-b border-white/5">
              <div className="absolute top-4 left-4 z-20 flex items-center gap-2 bg-black/60 backdrop-blur-md border border-white/10 px-3 py-1.5 rounded-lg text-xs font-bold">
                <Network size={14} className="text-[#3B82F6]" /> DEPENDENCY TOPOLOGY VIEW
              </div>
              <div className="absolute inset-0">
                {graphNodes.length > 0 && (
                  <FileGraph 
                    mode="static" 
                    nodes={graphNodes} 
                    edges={graphEdges} 
                    focusPath={graphNodes.filter(n => n.state === 'active').map(n => n.id)}
                    disableZoom={graphNodes.some(n => n.state === 'active')}
                    activeNodeStatus={activeFix?.status}
                    activeNodeLabel={activeFix && activeIdx !== null ? `TARGET: FIX-${(activeIdx + 1).toString().padStart(2, '0')}` : undefined}
                  />
                )}
              </div>
            </div>

            {/* Bottom details */}
            <div className="h-64 bg-[#05050A] p-4 flex gap-4 shrink-0 overflow-hidden">
              {activeFix ? (
                <>
                  <div className="w-1/3 flex flex-col gap-2">
                    <div className="text-[10px] font-bold text-gray-500 uppercase">Current Fix</div>
                    <div className="bg-white/5 border border-white/10 rounded-lg p-3 flex-1 flex flex-col">
                      <div className="font-bold text-sm text-gray-200 mb-1">{activeFix.finding.title}</div>
                      <div className="text-[10px] text-[#3B82F6] font-mono mb-2">{activeFix.finding.file}:{activeFix.finding.line}</div>
                      <div className="text-xs text-gray-400 flex-1 overflow-y-auto">{activeFix.finding.description}</div>
                    </div>
                  </div>
                  <div className="flex-1 flex flex-col gap-2">
                    <div className="text-[10px] font-bold text-gray-500 uppercase">Patch / Diff</div>
                    <div className="bg-black/60 border border-white/10 rounded-lg p-3 flex-1 overflow-y-auto font-mono text-xs text-gray-300">
                      {activeFix.patch ? (
                        <pre className="whitespace-pre-wrap">{activeFix.patch.diff}</pre>
                      ) : (
                        <div className="text-gray-600 flex items-center justify-center h-full italic">Waiting for patch generation...</div>
                      )}
                    </div>
                  </div>
                  <div className="w-48 flex flex-col gap-2">
                    <div className="text-[10px] font-bold text-gray-500 uppercase">Verification</div>
                    <div className="bg-white/5 border border-white/10 rounded-lg p-3 flex-1 flex flex-col gap-2 text-[10px] font-bold text-gray-400 uppercase">
                      {['patch', 'parse', 'analysis', 'security', 'test'].map((step) => (
                        <div key={step} className="flex items-center justify-between">
                          <span>{step}</span>
                          {pipelineState[step] === 'passed' ? <CheckCircle2 size={12} className="text-[#10B981]" /> :
                           pipelineState[step] === 'failed' ? <XCircle size={12} className="text-red-400" /> :
                           pipelineState[step] === 'running' ? <div className="w-2 h-2 rounded-full bg-[#3B82F6] animate-pulse" /> :
                           <div className="w-2 h-2 rounded-full border border-gray-600" />}
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              ) : sseState === 'completed' ? (
                <div className="flex-1 flex flex-col items-center justify-center text-center">
                  <CheckCircle2 size={32} className="text-[#10B981] mb-2" />
                  <div className="font-bold text-lg text-white">Sandbox Verification Complete</div>
                  <div className="text-sm text-gray-400 mb-4">{queue.filter(q => q.status === 'passed').length} verified, {queue.filter(q => q.status !== 'passed').length} failed/blocked.</div>
                  <div className="flex items-center justify-center gap-4">
                    <button className="px-6 py-2 bg-gradient-to-r from-[#6D5EF0] to-[#3B82F6] text-white font-bold rounded-lg text-sm" onClick={handleClose}>
                      Apply Verified Changes
                    </button>
                    <a 
                      href={`${API_BASE}/sandbox/download?session_id=${encodeURIComponent(sessionId)}`}
                      download
                      className="px-6 py-2 bg-white/10 hover:bg-white/20 border border-white/20 text-white font-bold rounded-lg text-sm transition-colors"
                    >
                      Extract Fixed Project
                    </a>
                  </div>
                </div>
              ) : (
                <div className="flex-1 flex items-center justify-center text-gray-500 text-sm">
                  Waiting for next fix to process...
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
