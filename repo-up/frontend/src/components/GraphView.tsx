import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Network, File, ArrowLeft, Search, Maximize, ShieldAlert, CheckCircle2, ChevronRight, ExternalLink } from 'lucide-react';
import { FileGraph } from './FileGraph';
import { CodeViewer } from './CodeViewer';

interface Finding {
  category: string;
  title: string;
  description: string;
  severity: "High" | "Medium" | "Low";
  file?: string;
  line?: number;
}

interface GraphViewProps {
  nodes: { id: string; label: string }[];
  edges: { source: string; target: string }[];
  issues?: Finding[];
  sessionId?: string;
  onClose: () => void;
}

export const GraphView: React.FC<GraphViewProps> = ({ nodes, edges, issues = [], sessionId, onClose }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [resetTrigger, setResetTrigger] = useState(0);
  const [focusPath, setFocusPath] = useState<string[]>([]);
  const [viewingFile, setViewingFile] = useState<{ path: string, line?: number, severity?: string } | null>(null);

  // Compute stats
  const stats = useMemo(() => {
    const totalFiles = nodes.length;
    const totalEdges = edges.length;
    
    // Find most connected node
    const degs: Record<string, number> = {};
    nodes.forEach(n => degs[n.id] = 0);
    edges.forEach(e => {
      if (degs[e.target] !== undefined) degs[e.target]++;
      if (degs[e.source] !== undefined) degs[e.source]++;
    });

    let maxNode = { id: '', degree: -1 };
    for (const [id, deg] of Object.entries(degs)) {
      if (deg > maxNode.degree) {
        maxNode = { id, degree: deg };
      }
    }
    const coreNode = nodes.find(n => n.id === maxNode.id)?.label || 'None';

    return { totalFiles, totalEdges, coreNode };
  }, [nodes, edges]);

  const handleNodeClick = (nodeId: string) => {
    setFocusPath(prev => {
      // If we clicked a node that's already in our path, just trim the path to that node.
      // Otherwise, add it to the path.
      const existingIdx = prev.indexOf(nodeId);
      if (existingIdx !== -1) {
        return prev.slice(0, existingIdx + 1);
      }
      return [...prev, nodeId];
    });
  };

  const handleResetView = () => {
    setFocusPath([]);
    setResetTrigger(prev => prev + 1);
  };

  const handleOpenFile = (filePath: string, line?: number, severity?: string) => {
    setViewingFile({ path: filePath, line, severity });
  };

  // Find info for currently focused node
  const focusedNodeId = focusPath.length > 0 ? focusPath[focusPath.length - 1] : null;
  const focusedNode = nodes.find(n => n.id === focusedNodeId);
  const focusedIssues = useMemo(() => {
    if (!focusedNode) return [];
    return issues.filter(i => {
      if (!i.file) return false;
      const issuePath = i.file.replace(/\\/g, '/');
      const nodePath = focusedNode.id.replace(/\\/g, '/');
      return issuePath === nodePath || issuePath.endsWith('/' + nodePath) || nodePath.endsWith('/' + issuePath);
    });
  }, [focusedNode, issues]);

  const hasCircularDep = useMemo(() => {
    return focusedIssues.some(i => i.title.includes("Circular Dependency"));
  }, [focusedIssues]);
  
  const getSeverityStyle = (sev: string) => {
    switch (sev?.toLowerCase()) {
      case 'high': return 'bg-[#991B1B]/20 text-[#F87171] border-[#F87171]/30';
      case 'medium': return 'bg-[#D97706]/20 text-[#FBBF24] border-[#FBBF24]/30';
      default: return 'bg-[#3B82F6]/20 text-[#3B82F6] border-[#3B82F6]/30';
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.98 }}
      className="fixed inset-0 z-50 bg-[#05050A] flex flex-col font-sans"
    >
      {/* HEADER */}
      <header className="h-16 border-b border-[#2A2E37] bg-[#0F1115]/80 backdrop-blur-md flex items-center justify-between px-6 shrink-0 relative z-20">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-[#1A1D23] border border-[#2A2E37] flex items-center justify-center text-primary-brand shadow-inner">
            <Network size={20} />
          </div>
          <div>
            <h1 className="font-bold text-white text-lg tracking-tight">Dependency Graph</h1>
            <p className="text-xs text-secondary-dark">Interactive architecture map</p>
          </div>
        </div>

        {/* Search */}
        <div className="flex-1 max-w-md mx-8 relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-secondary-dark" />
          <input 
            type="text" 
            placeholder="Search files to highlight..." 
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-[#13151A] border border-[#2A2E37] rounded-lg pl-9 pr-4 py-2 text-sm text-white placeholder:text-secondary-dark focus:outline-none focus:border-primary-brand/50 transition-colors"
          />
        </div>

        <button 
          onClick={onClose}
          className="flex items-center gap-2 text-sm font-medium text-secondary-dark hover:text-white bg-[#1A1D23] border border-[#2A2E37] hover:border-primary-brand/50 px-4 py-2 rounded-lg transition-all"
        >
          <ArrowLeft size={16} /> Back to results
        </button>
      </header>

      {/* GRAPH CANVAS */}
      <div className="flex-1 relative overflow-hidden bg-gradient-to-br from-[#0B0C10] to-[#0F1115] flex">
        <div className="flex-1 relative">
          <FileGraph 
            mode="static" 
            nodes={nodes} 
            edges={edges} 
            searchQuery={searchQuery}
            resetTrigger={resetTrigger}
            focusPath={focusPath}
            onNodeClick={handleNodeClick}
            issues={issues}
          />

          {/* Legend Panel (Bottom Left) */}
          <div className="absolute bottom-6 left-6 bg-[#0F1115]/80 backdrop-blur-md border border-[#2A2E37] p-4 rounded-xl shadow-2xl pointer-events-none">
            <h4 className="text-[10px] font-bold text-secondary-dark uppercase tracking-wider mb-3">Directory Legend</h4>
            <ul className="space-y-2 text-xs font-medium text-gray-300">
              <li className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full bg-[#2DD4A7]" /> components/</li>
              <li className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full bg-[#6D5EF0]" /> services/ | api/</li>
              <li className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full bg-[#3B82F6]" /> utils/ | helpers/</li>
              <li className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full bg-[#9CA3AF]" /> tests/</li>
              <li className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full bg-[#4B5563]" /> other files</li>
            </ul>
          </div>

          {/* Stats Panel (Top Right) */}
          <div className="absolute top-6 right-6 bg-[#0F1115]/80 backdrop-blur-md border border-[#2A2E37] p-4 rounded-xl shadow-2xl flex gap-6">
            <div>
              <div className="text-[10px] font-bold text-secondary-dark uppercase tracking-wider mb-1">Total Files</div>
              <div className="text-xl font-bold text-white flex items-center gap-2">
                <File size={16} className="text-primary-brand" /> {stats.totalFiles}
              </div>
            </div>
            <div className="w-px bg-[#2A2E37]" />
            <div>
              <div className="text-[10px] font-bold text-secondary-dark uppercase tracking-wider mb-1">Dependencies</div>
              <div className="text-xl font-bold text-white flex items-center gap-2">
                <Network size={16} className="text-[#3B82F6]" /> {stats.totalEdges}
              </div>
            </div>
            <div className="w-px bg-[#2A2E37]" />
            <div>
              <div className="text-[10px] font-bold text-secondary-dark uppercase tracking-wider mb-1">Core Node</div>
              <div className="text-sm font-mono font-bold text-[#6D5EF0] bg-[#6D5EF0]/10 px-2 py-0.5 rounded border border-[#6D5EF0]/20 mt-1">
                {stats.coreNode}
              </div>
            </div>
          </div>

          {/* Controls (Bottom Right) */}
          <div className="absolute bottom-6 right-6 flex flex-col gap-2">
            <div className="bg-[#0F1115]/80 backdrop-blur-md border border-[#2A2E37] p-3 rounded-xl shadow-2xl flex flex-col gap-3">
              <div className="text-[10px] font-bold text-secondary-dark uppercase tracking-wider text-center">Controls</div>
              <div className="flex items-center gap-2 text-xs text-gray-400">
                <div className="px-1.5 py-0.5 bg-[#1A1D23] border border-[#2A2E37] rounded">Scroll</div>
                <span>to zoom</span>
              </div>
              <div className="flex items-center gap-2 text-xs text-gray-400">
                <div className="px-1.5 py-0.5 bg-[#1A1D23] border border-[#2A2E37] rounded">Drag</div>
                <span>to pan</span>
              </div>
              <button 
                onClick={handleResetView}
                className="mt-2 w-full py-1.5 bg-[#1A1D23] hover:bg-[#2A2E37] border border-[#2A2E37] rounded-lg text-xs font-medium text-white transition-colors flex items-center justify-center gap-1.5"
              >
                <Maximize size={12} /> Reset View
              </button>
            </div>
          </div>
        </div>

        {/* SIDE PANEL FOR FOCUS MODE */}
        <AnimatePresence>
          {focusedNode && (
            <motion.div
              initial={{ x: 400, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: 400, opacity: 0 }}
              transition={{ type: "spring", damping: 25, stiffness: 200 }}
              className="w-96 bg-[#0B0C10]/60 backdrop-blur-[16px] border-l border-white/10 shrink-0 flex flex-col shadow-2xl relative z-30"
            >
              {/* Breadcrumb Header */}
              <div className="p-4 border-b border-white/10 bg-black/20 flex flex-wrap gap-1 text-[10px] font-mono text-gray-400 items-center">
                {focusPath.map((id, idx) => {
                  const node = nodes.find(n => n.id === id);
                  const isLast = idx === focusPath.length - 1;
                  if (!node) return null;
                  return (
                    <React.Fragment key={id}>
                      <button 
                        onClick={() => handleNodeClick(id)}
                        className={`hover:text-white transition-colors ${isLast ? 'text-white font-bold' : ''}`}
                      >
                        {node.label.split('/').pop()}
                      </button>
                      {!isLast && <ChevronRight size={10} className="mx-0.5" />}
                    </React.Fragment>
                  );
                })}
              </div>

              {/* Node Detail */}
              <div className="p-6 flex-1 overflow-y-auto">
                <div className="mb-6">
                  <div className="flex items-start justify-between mb-2">
                    <h2 className="text-xl font-bold text-white break-all">{focusedNode.label.split('/').pop()}</h2>
                    <button 
                      onClick={handleResetView}
                      className="p-1.5 hover:bg-white/10 rounded-lg text-gray-400 hover:text-white transition-colors"
                      title="Close focus view"
                    >
                      <X size={16} />
                    </button>
                  </div>
                  <p className="text-xs text-gray-400 font-mono break-all mb-3">{focusedNode.label}</p>
                  
                  <button 
                    onClick={() => handleOpenFile(focusedNode.id)}
                    className="flex items-center gap-2 text-xs font-medium text-white bg-white/5 hover:bg-white/10 border border-white/10 hover:border-white/20 px-3 py-1.5 rounded-lg transition-all"
                  >
                    <ExternalLink size={12} /> View Source Code
                  </button>
                </div>
                
                {hasCircularDep && (
                  <div className="mb-6 px-3 py-2 bg-gradient-to-r from-purple-500/10 to-blue-500/10 border border-purple-500/30 rounded-lg flex items-start gap-3">
                    <Network size={16} className="text-purple-400 shrink-0 mt-0.5" />
                    <div>
                      <h4 className="text-xs font-bold text-white mb-1">Part of Circular Dependency</h4>
                      <p className="text-[10px] text-gray-400">This file is caught in a cycle. See findings below.</p>
                    </div>
                  </div>
                )}

                <div>
                  <h3 className="font-bold flex items-center gap-2 text-white mb-4 border-b border-white/10 pb-2">
                    <ShieldAlert size={14} className="text-[#F59E0B]" /> Findings
                  </h3>
                  
                  {focusedIssues.length === 0 ? (
                    <div className="text-center py-10 px-4 text-sm text-gray-400 flex flex-col items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-[#10B981]/10 flex items-center justify-center">
                        <CheckCircle2 size={20} className="text-[#10B981]" />
                      </div>
                      <p>No issues detected in this file.</p>
                    </div>
                  ) : (
                    <ul className="space-y-4">
                      {focusedIssues.map((issue, idx) => (
                        <li 
                          key={idx} 
                          onClick={() => handleOpenFile(focusedNode.id, issue.line, issue.severity)}
                          className="bg-black/40 border border-white/5 hover:border-white/20 hover:bg-white/5 p-3 rounded-lg flex flex-col gap-2 cursor-pointer transition-colors group"
                        >
                          <div className="flex items-start justify-between">
                            <span className="font-semibold text-sm text-gray-200 group-hover:text-white transition-colors">{issue.title}</span>
                            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border shrink-0 ${getSeverityStyle(issue.severity)}`}>
                              {issue.severity || 'Medium'}
                            </span>
                          </div>
                          <p className="text-xs text-gray-400 leading-relaxed">
                            {issue.description.replace(/([A-Za-z0-9_]{4})[A-Za-z0-9_]{8,}([A-Za-z0-9_]{4})/g, '$1••••••••$2')}
                          </p>
                          {issue.line && (
                            <div className="flex items-center gap-1.5 mt-1 text-[10px] font-mono text-gray-500">
                              <ExternalLink size={10} />
                              Jump to line {issue.line}
                            </div>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* INLINE CODE VIEWER MODAL */}
        <AnimatePresence>
          {viewingFile && sessionId && (
            <CodeViewer 
              sessionId={sessionId}
              filePath={viewingFile.path}
              line={viewingFile.line}
              fileIssues={focusedIssues}
              onClose={() => setViewingFile(null)}
            />
          )}
        </AnimatePresence>

      </div>
    </motion.div>
  );
};
