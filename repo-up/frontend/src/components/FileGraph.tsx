import React, { useMemo, useEffect, useState, useRef } from 'react';
import { motion } from 'framer-motion';
import * as d3Force from 'd3-force';
import * as d3Zoom from 'd3-zoom';
import { select } from 'd3-selection';
import 'd3-transition';

interface Finding {
  category: string;
  title: string;
  description: string;
  severity: "High" | "Medium" | "Low";
  file?: string;
}

export interface FileGraphProps {
  nodes: { id: string; label: string }[];
  edges: { source: string; target: string }[];
  mode: 'animated-reveal' | 'static' | 'streaming';
  searchQuery?: string;
  resetTrigger?: number;
  onRevealComplete?: () => void;
  // Focus Mode Props
  focusPath?: string[];
  onNodeClick?: (nodeId: string) => void;
  issues?: Finding[];
  disableZoom?: boolean;
  activeNodeStatus?: string;
  activeNodeLabel?: string;
}

interface ForceNode extends d3Force.SimulationNodeDatum {
  id: string;
  label: string;
  inDegree: number;
  outDegree: number;
  degree: number;
  color: string;
  radius: number;
  bfsDistance: number;
  severityLevel?: 'high' | 'medium' | null;
}

interface ForceEdge extends d3Force.SimulationLinkDatum<ForceNode> {
  source: ForceNode;
  target: ForceNode;
}

export const FileGraph: React.FC<FileGraphProps> = ({ 
  nodes, 
  edges, 
  mode, 
  searchQuery, 
  resetTrigger, 
  onRevealComplete,
  focusPath = [],
  onNodeClick,
  issues = [],
  disableZoom = false,
  activeNodeStatus,
  activeNodeLabel
}) => {
  const VIEWBOX_WIDTH = 1200;
  const VIEWBOX_HEIGHT = 800;

  const isAnimated = mode === 'animated-reveal';
  const isStreaming = mode === 'streaming';
  
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [zoomScale, setZoomScale] = useState<number>(1);
  const svgRef = useRef<SVGSVGElement>(null);
  const gRef = useRef<SVGGElement>(null);
  const zoomRef = useRef<d3Zoom.ZoomBehavior<SVGSVGElement, unknown> | null>(null);
  
  const disableZoomRef = useRef(disableZoom);
  useEffect(() => { disableZoomRef.current = disableZoom; }, [disableZoom]);

  const getFolderColor = (path: string) => {
    const normalizedPath = path.replace(/\\/g, '/');
    if (normalizedPath.includes('components/')) return '#2DD4A7'; // Teal
    if (normalizedPath.includes('services/') || normalizedPath.includes('api/')) return '#6D5EF0'; // Purple
    if (normalizedPath.includes('utils/') || normalizedPath.includes('helpers/')) return '#3B82F6'; // Blue
    if (normalizedPath.includes('tests/')) return '#9CA3AF'; // Gray
    return '#4B5563'; // Slate
  };

  const layoutData = useMemo(() => {
    if (!nodes || nodes.length === 0) return { positionedNodes: [], edgeMap: [], nodeMap: {}, maxDist: 1, coreNode: null };

    // 1. Calculate degrees & issue severity
    const degs: Record<string, { in: number, out: number }> = {};
    const severityMap: Record<string, 'high' | 'medium' | null> = {};
    
    nodes.forEach(n => {
      degs[n.id] = { in: 0, out: 0 };
      const nodeIssues = issues.filter(i => i.file && i.file.includes(n.label));
      if (nodeIssues.some(i => i.severity.toLowerCase() === 'high')) {
        severityMap[n.id] = 'high';
      } else if (nodeIssues.some(i => i.severity.toLowerCase() === 'medium')) {
        severityMap[n.id] = 'medium';
      } else {
        severityMap[n.id] = null;
      }
    });
    
    edges.forEach(e => {
      if (degs[e.target]) degs[e.target].in += 1;
      if (degs[e.source]) degs[e.source].out += 1;
    });

    // 2. Prepare nodes for D3
    const forceNodes: ForceNode[] = nodes.map(n => {
      const d = degs[n.id] || { in: 0, out: 0 };
      const degree = d.in + d.out;
      return {
        ...n,
        inDegree: d.in,
        outDegree: d.out,
        degree,
        color: getFolderColor(n.id),
        radius: degree === 0 ? 6 : Math.min(24, 6 + (degree * 1.5)),
        bfsDistance: 0,
        severityLevel: severityMap[n.id]
      };
    });

    const nodeMap = forceNodes.reduce((acc, curr) => { 
      acc[curr.id] = curr; 
      return acc; 
    }, {} as Record<string, ForceNode>);

    // 3. BFS for reveal animation
    const sortedByDegree = [...forceNodes].sort((a, b) => b.degree - a.degree);
    const coreNode = sortedByDegree[0];
    
    const adj: Record<string, string[]> = {};
    edges.forEach(e => {
       if (!adj[e.source]) adj[e.source] = [];
       if (!adj[e.target]) adj[e.target] = [];
       adj[e.source].push(e.target);
       adj[e.target].push(e.source);
    });

    if (coreNode && edges.length > 0) {
       const visited = new Set<string>();
       const queue = [{ id: coreNode.id, dist: 0 }];
       visited.add(coreNode.id);
       
       while (queue.length > 0) {
           const curr = queue.shift()!;
           if (nodeMap[curr.id]) {
               nodeMap[curr.id].bfsDistance = curr.dist;
           }
           const neighbors = adj[curr.id] || [];
           for (const nbr of neighbors) {
               if (!visited.has(nbr)) {
                   visited.add(nbr);
                   queue.push({ id: nbr, dist: curr.dist + 1 });
               }
           }
       }
       const maxDistFound = Math.max(0, ...forceNodes.map(n => n.bfsDistance));
       forceNodes.forEach(n => {
           if (!visited.has(n.id)) n.bfsDistance = maxDistFound + 1;
       });
    }
    
    const maxDist = Math.max(1, ...forceNodes.map(n => n.bfsDistance));

    // 4. Prepare edges for D3
    const forceEdges: any[] = edges
      .filter(e => nodeMap[e.source] && nodeMap[e.target])
      .map(e => ({ source: e.source, target: e.target }));

    // 5. Run static force simulation
    const repulsionStrength = forceNodes.length < 15 ? -100 : forceNodes.length < 50 ? -200 : -300;
    
    const simulation = d3Force.forceSimulation(forceNodes)
      .force("link", d3Force.forceLink(forceEdges).id((d: any) => d.id).distance(40))
      .force("charge", d3Force.forceManyBody().strength(repulsionStrength))
      .force("center", d3Force.forceCenter(VIEWBOX_WIDTH / 2, VIEWBOX_HEIGHT / 2))
      .force("x", d3Force.forceX(VIEWBOX_WIDTH / 2).strength(0.03))
      .force("y", d3Force.forceY(VIEWBOX_HEIGHT / 2).strength(0.03))
      .force("collide", d3Force.forceCollide().radius((d: any) => d.radius + 10))
      .stop();

    // Run statically to cache positions
    const iterations = Math.min(200, Math.max(50, forceNodes.length * 2));
    for (let i = 0; i < iterations; i++) {
      simulation.tick();
    }

    return { 
      positionedNodes: forceNodes, 
      edgeMap: forceEdges as ForceEdge[], 
      nodeMap, 
      maxDist, 
      coreNode 
    };
  }, [nodes, edges, issues]);

  const { positionedNodes, edgeMap, maxDist, nodeMap } = layoutData;

  const maxNodeStagger = 1.5;
  const nodeStaggerStep = maxNodeStagger / maxDist;

  useEffect(() => {
    if (isAnimated && onRevealComplete && nodes.length > 0) {
      const totalAnimationTime = maxNodeStagger + 1.5;
      const timer = setTimeout(() => {
        onRevealComplete();
      }, totalAnimationTime * 1000);
      return () => clearTimeout(timer);
    }
  }, [isAnimated, onRevealComplete, nodes.length, maxNodeStagger]);

  // Handle D3 Zoom Setup
  useEffect(() => {
    if (!svgRef.current || !gRef.current) return;

    const svg = select(svgRef.current);
    const g = select(gRef.current);

    const zoom = d3Zoom.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 5])
      .filter((event) => {
         // Default D3 zoom filter behavior + our custom disable flag
         return !disableZoomRef.current && (!event.ctrlKey || event.type === 'wheel') && !event.button;
      })
      .on('zoom', (event) => {
        g.attr('transform', event.transform);
        setZoomScale(event.transform.k);
      });

    svg.call(zoom);
    zoomRef.current = zoom;
    
    if (resetTrigger && resetTrigger > 0) {
      svg.transition().duration(750).call(zoom.transform, d3Zoom.zoomIdentity);
    }
  }, [resetTrigger, nodes.length]);

  // Handle Focus Mode Camera Pan
  const focusedNodeId = focusPath.length > 0 ? focusPath[focusPath.length - 1] : null;
  
  useEffect(() => {
    if (focusedNodeId && svgRef.current && zoomRef.current && (nodeMap as Record<string, ForceNode>)[focusedNodeId]) {
      const targetNode = (nodeMap as Record<string, ForceNode>)[focusedNodeId];
      if (targetNode.x !== undefined && targetNode.y !== undefined) {
        const svg = select(svgRef.current);
        // Desired scale
        const scale = 2.5;
        // We calculate pan by considering SVG client dimensions but the viewport coordinate system is fixed to viewBox size
        // Since viewBox uses width/height, we map to that.
        const tx = VIEWBOX_WIDTH / 2 - targetNode.x * scale;
        const ty = VIEWBOX_HEIGHT / 2 - targetNode.y * scale;

        svg.transition()
          .duration(750)
          .call(zoomRef.current.transform, d3Zoom.zoomIdentity.translate(tx, ty).scale(scale));
      }
    }
  }, [focusedNodeId, nodeMap]);

  // Calculate overridden positions for focus mode
  const displayNodes = useMemo(() => {
    // Make a copy of nodes so we don't mutate the cached D3 positions
    const nodesCopy = positionedNodes.map(n => ({ ...n }));
    if (!focusedNodeId) return nodesCopy;

    const focusedIndex = nodesCopy.findIndex(n => n.id === focusedNodeId);
    if (focusedIndex === -1) return nodesCopy;

    const fNode = nodesCopy[focusedIndex];
    if (fNode.x === undefined || fNode.y === undefined) return nodesCopy;

    // Find neighbors
    const neighborIds = new Set<string>();
    edgeMap.forEach(e => {
      if (e.source.id === focusedNodeId) neighborIds.add(e.target.id);
      if (e.target.id === focusedNodeId) neighborIds.add(e.source.id);
    });

    const neighbors = nodesCopy.filter(n => neighborIds.has(n.id));
    
    // Calculate orbit radius scaling based on neighbor count
    const baseRadius = 100;
    const spacingFactor = 15; // Adds 15px radius per neighbor to avoid crowding
    const orbitRadius = baseRadius + (neighbors.length * spacingFactor);

    // Position neighbors in a circle
    neighbors.forEach((nbr, i) => {
      const angle = (i / neighbors.length) * Math.PI * 2;
      nbr.x = fNode.x! + orbitRadius * Math.cos(angle);
      nbr.y = fNode.y! + orbitRadius * Math.sin(angle);
    });

    return nodesCopy;
  }, [positionedNodes, edgeMap, focusedNodeId]);

  return (
    <div className="w-full h-full relative overflow-hidden flex items-center justify-center">
      {nodes.length === 0 && mode !== 'streaming' ? (
        <div className="text-secondary-dark text-sm z-10 absolute">No graph data available</div>
      ) : (
        <svg 
          ref={svgRef}
          viewBox={`0 0 ${VIEWBOX_WIDTH} ${VIEWBOX_HEIGHT}`} 
          className="w-full h-full z-10 drop-shadow-md cursor-grab active:cursor-grabbing"
        >
          <defs>
            <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="6" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
            
            {/* Animated gradient for focused edges */}
            <linearGradient id="pulseGrad" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#2DD4A7" stopOpacity="0.2">
                <animate attributeName="offset" values="-1; 1" dur="1.5s" repeatCount="indefinite" />
              </stop>
              <stop offset="50%" stopColor="#6D5EF0" stopOpacity="1">
                <animate attributeName="offset" values="0; 2" dur="1.5s" repeatCount="indefinite" />
              </stop>
              <stop offset="100%" stopColor="#2DD4A7" stopOpacity="0.2">
                <animate attributeName="offset" values="1; 3" dur="1.5s" repeatCount="indefinite" />
              </stop>
            </linearGradient>
          </defs>

          <g ref={gRef}>
            {/* EDGES */}
            <g className="edges">
              {edgeMap.map((e, _idx) => {
                const src = displayNodes.find(n => n.id === e.source.id);
                const tgt = displayNodes.find(n => n.id === e.target.id);
                if (!src || !tgt || src.x === undefined || src.y === undefined || tgt.x === undefined || tgt.y === undefined) return null;

                const dx = tgt.x - src.x;
                const dy = tgt.y - src.y;
                const cx = src.x + dx/2 + dy*0.15;
                const cy = src.y + dy/2 - dx*0.15;
                const path = `M${src.x},${src.y} Q${cx},${cy} ${tgt.x},${tgt.y}`;

                const isConnectedToHovered = hoveredNode === src.id || hoveredNode === tgt.id;
                const isSearched = searchQuery && (src.label.toLowerCase().includes(searchQuery.toLowerCase()) || tgt.label.toLowerCase().includes(searchQuery.toLowerCase()));
                const isConnectedToFocused = focusedNodeId === src.id || focusedNodeId === tgt.id;
                
                let isFaded = false;
                if (focusedNodeId) {
                  isFaded = !isConnectedToFocused;
                } else if (hoveredNode) {
                  isFaded = !isConnectedToHovered;
                } else if (searchQuery) {
                  isFaded = !isSearched;
                }

                const edgeDelay = isAnimated ? Math.max(src.bfsDistance, tgt.bfsDistance) * nodeStaggerStep + 0.2 : 0;
                
                // If it's connected to focused node, use the pulse gradient
                const strokeStyle = isConnectedToFocused ? "url(#pulseGrad)" : "#2DD4A7";

                return (
                  <motion.path
                    key={`edge-${src.id}-${tgt.id}`}
                    d={path}
                    fill="none"
                    stroke={strokeStyle}
                    strokeWidth={isConnectedToFocused ? "2" : "1.5"}
                    style={{ filter: isFaded ? 'grayscale(60%)' : 'none' }}
                    className="transition-all duration-300 pointer-events-none"
                    initial={(isAnimated || isStreaming) ? { pathLength: 0, opacity: 0 } : { pathLength: 1, opacity: isFaded ? 0.05 : 0.7 }}
                    animate={{ 
                      pathLength: 1, 
                      opacity: isFaded ? 0.05 : (isConnectedToHovered || isConnectedToFocused) ? 1.0 : searchQuery ? 0.1 : 0.7
                    }}
                    transition={{ 
                      delay: edgeDelay, 
                      duration: 0.6,
                      ease: "easeInOut"
                    }}
                  />
                );
              })}
            </g>

            {/* NODES */}
            <g className="nodes">
              {displayNodes.map((n) => {
                const isHovered = hoveredNode === n.id;
                const isSearched = searchQuery && n.label.toLowerCase().includes(searchQuery.toLowerCase());
                const isFocused = focusedNodeId === n.id;
                
                const isNeighborToFocused = focusedNodeId && edgeMap.some(e => {
                  return (e.source.id === n.id && e.target.id === focusedNodeId) || (e.target.id === n.id && e.source.id === focusedNodeId);
                });

                let isFaded = false;
                if (focusedNodeId) {
                  isFaded = !isFocused && !isNeighborToFocused;
                } else if (hoveredNode) {
                  isFaded = !isHovered && !edgeMap.some(e => {
                    return (e.source.id === n.id && e.target.id === hoveredNode) || (e.target.id === n.id && e.source.id === hoveredNode);
                  });
                } else if (searchQuery) {
                  isFaded = !isSearched;
                }

                // Hide labels if dense, unless highly connected, hovered, searched, focused, or zoom > 1.4
                const showLabel = nodes.length <= 20 || n.degree > 4 || isHovered || isSearched || isFocused || isNeighborToFocused || zoomScale > 1.4;
                const isIsolated = n.degree === 0;

                // Determine node color for active state
                let focusColor = n.color;
                if (isFocused && activeNodeStatus) {
                  if (activeNodeStatus === 'running') focusColor = '#EAB308'; // Yellow
                  else if (activeNodeStatus === 'passed') focusColor = '#10B981'; // Green
                  else focusColor = '#EF4444'; // Red for queued/blocked/failed
                }

                return (
                  <motion.g 
                    key={`node-${n.id}`} 
                    className="cursor-pointer"
                    onMouseEnter={() => setHoveredNode(n.id)}
                    onMouseLeave={() => setHoveredNode(null)}
                    onClick={(e) => {
                      e.stopPropagation();
                      if (onNodeClick) onNodeClick(n.id);
                    }}
                    initial={(isAnimated || isStreaming) ? { scale: 0, opacity: 0, x: n.x, y: n.y } : { scale: 1, opacity: isIsolated ? 0.4 : 1, x: n.x, y: n.y }}
                    animate={{ 
                      scale: isFocused ? 1.25 : (isHovered || isSearched ? 1.2 : 1), 
                      opacity: isFaded ? 0.1 : isIsolated ? 0.4 : 1,
                      x: n.x,
                      y: n.y
                    }}
                    style={{ filter: isFaded ? 'grayscale(60%)' : 'none' }}
                    transition={{ 
                      delay: isAnimated ? n.bfsDistance * nodeStaggerStep : 0,
                      type: "spring",
                      stiffness: 260,
                      damping: 20
                    }}
                  >
                    {/* Pre-focus Severity Pulse (behind node) */}
                    {!focusedNodeId && n.severityLevel && (
                      <circle
                        r={n.radius * 2}
                        fill="none"
                        stroke={n.severityLevel === 'high' ? "#EF4444" : "#F59E0B"}
                        strokeWidth="2"
                        opacity="0.6"
                      >
                        <animate attributeName="r" values={`${n.radius};${n.radius * 3}`} dur="2s" repeatCount="indefinite" />
                        <animate attributeName="opacity" values="0.6;0" dur="2s" repeatCount="indefinite" />
                      </circle>
                    )}

                    {/* Outer glow for focused node */}
                    {isFocused && (
                        <circle
                            r={n.radius * 2.5}
                            fill={focusColor}
                            opacity="0.15"
                            filter="url(#glow)"
                        />
                    )}

                    {/* Base Node Styling */}
                    <circle
                      r={n.radius}
                      fill="#05050A"
                      stroke={isFocused ? focusColor : n.color}
                      strokeWidth="3"
                      className="transition-colors duration-300"
                    />
                    
                    {/* Inner dash ring for focused node */}
                    {isFocused && (
                      <circle
                        r={n.radius * 0.7}
                        fill="none"
                        stroke={focusColor}
                        strokeWidth="1.5"
                        strokeDasharray="2,2"
                        className="transition-colors duration-300"
                      />
                    )}

                    {/* Center solid core */}
                    <circle
                      r={n.radius * 0.4}
                      fill={isFocused ? focusColor : n.color}
                      opacity={isFocused ? 1 : 0.9}
                      className="transition-colors duration-300"
                    />

                    {/* Target Label (Top) */}
                    {isFocused && activeNodeLabel && (
                        <foreignObject 
                            x="-75" y={-n.radius - 30} width="150" height="24"
                            className="overflow-visible"
                        >
                            <div className="flex justify-center items-center pointer-events-none w-full">
                                <span className="px-2 py-0.5 rounded font-mono text-[9px] font-bold tracking-wider" 
                                      style={{ backgroundColor: focusColor + '20', color: focusColor, border: `1px solid ${focusColor}40` }}>
                                    {activeNodeLabel}
                                </span>
                            </div>
                        </foreignObject>
                    )}

                    {/* Node Name Label (Bottom) */}
                    {showLabel && (
                        <foreignObject 
                            x="-75" y={n.radius + 8} width="150" height="24"
                            className="overflow-visible"
                        >
                            <div className="flex justify-center items-center pointer-events-none w-full">
                                <span className={`px-2 py-0.5 rounded-md border bg-[#05050A]/80 font-mono text-[10px] whitespace-nowrap transition-all duration-300 ${isHovered || isSearched || isFocused ? 'text-gray-200 border-white/20 font-medium shadow-md' : 'text-gray-500 border-white/5'}`}>
                                    {n.label.split('/').pop()}
                                </span>
                            </div>
                        </foreignObject>
                    )}
                  </motion.g>
                );
              })}
            </g>
          </g>
        </svg>
      )}
    </div>
  );
};
