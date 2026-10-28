import React, { useEffect, useRef } from "react";

interface Node {
  id: number;
  relX: number;
  relY: number;
  x: number;
  y: number;
  baseX: number;
  baseY: number;
  radius: number;
  type: "hub" | "primary" | "secondary" | "leaf";
  isWarning: boolean;
  warningColor?: string;
  connections: number[];
  phaseX: number;
  phaseY: number;
  driftSpeed: number;
  driftRange: number;
}

interface Pulse {
  path: number[];
  currentEdgeIndex: number;
  progress: number; // 0 to 1
  speed: number;
}

export const DependencyGraphBackground: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationFrameId: number;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    // Node count: ~48 nodes
    const nodes: Node[] = [];
    const totalNodes = 48;

    // Helper to generate coordinates clustered or scattered
    const generateNodes = () => {
      nodes.length = 0;

      // 1. Create Hubs
      // Hub 1: Center-Left
      nodes.push({
        id: 0,
        relX: 0.22,
        relY: 0.45,
        x: 0,
        y: 0,
        baseX: 0,
        baseY: 0,
        radius: 11,
        type: "hub",
        isWarning: false,
        connections: [],
        phaseX: Math.random() * Math.PI * 2,
        phaseY: Math.random() * Math.PI * 2,
        driftSpeed: 0.0004,
        driftRange: 8,
      });

      // Hub 2: Middle-Bottom-Left
      nodes.push({
        id: 1,
        relX: 0.38,
        relY: 0.62,
        x: 0,
        y: 0,
        baseX: 0,
        baseY: 0,
        radius: 9.5,
        type: "hub",
        isWarning: false,
        connections: [],
        phaseX: Math.random() * Math.PI * 2,
        phaseY: Math.random() * Math.PI * 2,
        driftSpeed: 0.0003,
        driftRange: 6,
      });

      // 2. Create Primary Nodes (branching from hubs)
      const primaryCount = 10;
      for (let i = 0; i < primaryCount; i++) {
        const parentHubId = i < 6 ? 0 : 1;
        const angle = (i / primaryCount) * Math.PI * 2 + Math.random() * 0.5;
        const dist = 0.08 + Math.random() * 0.07;
        const parentHub = nodes[parentHubId];

        const relX = parentHub.relX + Math.cos(angle) * dist;
        const relY = parentHub.relY + Math.sin(angle) * dist * 1.3; // Aspect ratio adjustment

        nodes.push({
          id: nodes.length,
          relX: Math.max(0.05, Math.min(0.95, relX)),
          relY: Math.max(0.05, Math.min(0.95, relY)),
          x: 0,
          y: 0,
          baseX: 0,
          baseY: 0,
          radius: 6.5 + Math.random() * 1.5,
          type: "primary",
          isWarning: false,
          connections: [parentHubId],
          phaseX: Math.random() * Math.PI * 2,
          phaseY: Math.random() * Math.PI * 2,
          driftSpeed: 0.0006 + Math.random() * 0.0006,
          driftRange: 12 + Math.random() * 6,
        });

        // Add bidirectional connection
        nodes[parentHubId].connections.push(nodes.length - 1);
      }

      // 3. Create Secondary Nodes (branching from primary nodes)
      const secondaryCount = 16;
      for (let i = 0; i < secondaryCount; i++) {
        // Pick a random primary node as parent
        const parentIndex = 2 + Math.floor(Math.random() * primaryCount);
        const parentNode = nodes[parentIndex];
        const angle = Math.random() * Math.PI * 2;
        const dist = 0.07 + Math.random() * 0.06;

        const relX = parentNode.relX + Math.cos(angle) * dist;
        const relY = parentNode.relY + Math.sin(angle) * dist * 1.3;

        nodes.push({
          id: nodes.length,
          relX: Math.max(0.05, Math.min(0.95, relX)),
          relY: Math.max(0.05, Math.min(0.95, relY)),
          x: 0,
          y: 0,
          baseX: 0,
          baseY: 0,
          radius: 4.5 + Math.random() * 1.5,
          type: "secondary",
          isWarning: false,
          connections: [parentIndex],
          phaseX: Math.random() * Math.PI * 2,
          phaseY: Math.random() * Math.PI * 2,
          driftSpeed: 0.0008 + Math.random() * 0.0008,
          driftRange: 15 + Math.random() * 8,
        });

        nodes[parentIndex].connections.push(nodes.length - 1);
      }

      // 4. Create Leaf Nodes
      const leafCount = totalNodes - nodes.length;
      for (let i = 0; i < leafCount; i++) {
        // Pick a random secondary node
        const parentIndex =
          2 + primaryCount + Math.floor(Math.random() * secondaryCount);
        const parentNode = nodes[parentIndex];
        const angle = Math.random() * Math.PI * 2;
        const dist = 0.06 + Math.random() * 0.05;

        const relX = parentNode.relX + Math.cos(angle) * dist;
        const relY = parentNode.relY + Math.sin(angle) * dist * 1.3;

        nodes.push({
          id: nodes.length,
          relX: Math.max(0.05, Math.min(0.95, relX)),
          relY: Math.max(0.05, Math.min(0.95, relY)),
          x: 0,
          y: 0,
          baseX: 0,
          baseY: 0,
          radius: 3.5 + Math.random() * 1.0,
          type: "leaf",
          isWarning: false,
          connections: [parentIndex],
          phaseX: Math.random() * Math.PI * 2,
          phaseY: Math.random() * Math.PI * 2,
          driftSpeed: 0.001 + Math.random() * 0.001,
          driftRange: 18 + Math.random() * 10,
        });

        nodes[parentIndex].connections.push(nodes.length - 1);
      }

      // 5. Add cross-connections between nearby nodes (to create cycles and mesh feel)
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          // Calculate relative distance
          const dx = nodes[i].relX - nodes[j].relX;
          const dy = nodes[i].relY - nodes[j].relY;
          const dist = Math.sqrt(dx * dx + dy * dy);

          // If close enough, not hubs, and haven't reached connection cap
          if (
            dist < 0.11 &&
            nodes[i].type !== "hub" &&
            nodes[j].type !== "hub" &&
            nodes[i].connections.length < 3 &&
            nodes[j].connections.length < 3 &&
            !nodes[i].connections.includes(j)
          ) {
            nodes[i].connections.push(j);
            nodes[j].connections.push(i);
          }
        }
      }

      // 6. Assign 2-3 Warning Nodes
      // Pick 2-3 nodes at random from primary or secondary list (not hubs)
      const warningIndices = [
        3 + Math.floor(Math.random() * 5), // in primary
        15 + Math.floor(Math.random() * 10), // in secondary/leaf
      ];

      warningIndices.forEach((idx, i) => {
        if (nodes[idx] && nodes[idx].type !== "hub") {
          nodes[idx].isWarning = true;
          // One red, one amber
          nodes[idx].warningColor = i === 0 ? "#EF4444" : "#F59E0B";
          // Make warning nodes drift extremely slowly
          nodes[idx].driftSpeed = 0.0001;
          nodes[idx].driftRange = 3;
        }
      });
    };

    generateNodes();

    // Resize handler
    const updatePositions = () => {
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;

      // Update absolute coordinates based on relative positions
      nodes.forEach((node) => {
        node.baseX = node.relX * width;
        node.baseY = node.relY * height;
        // Keep actual coordinates close to base initially
        if (node.x === 0 && node.y === 0) {
          node.x = node.baseX;
          node.y = node.baseY;
        }
      });
    };

    updatePositions();
    window.addEventListener("resize", updatePositions);

    // Track active signal pulses
    const activePulses: Pulse[] = [];

    // Simple DFS path-finder to build a path from hub to a leaf node
    const findPathToLeaf = (startId: number): number[] => {
      const path: number[] = [startId];
      let current = startId;
      const visited = new Set<number>([startId]);

      // Move away from the start
      while (true) {
        const neighbors = nodes[current].connections.filter(
          (n) => !visited.has(n),
        );
        if (neighbors.length === 0) break;

        // Sort neighbors by distance from hub to propagate outwards
        const startNode = nodes[startId];
        neighbors.sort((a, b) => {
          const distA = Math.hypot(
            nodes[a].relX - startNode.relX,
            nodes[a].relY - startNode.relY,
          );
          const distB = Math.hypot(
            nodes[b].relX - startNode.relX,
            nodes[b].relY - startNode.relY,
          );
          return distB - distA; // prefer larger distance first (outward propagation)
        });

        // Add some randomness to selections (choose from top 2 neighbors)
        const candidates = neighbors.slice(0, 2);
        const next = candidates[Math.floor(Math.random() * candidates.length)];

        path.push(next);
        visited.add(next);
        current = next;

        // Stop if we reach a leaf node or a node with no connections other than visited
        if (nodes[current].type === "leaf" || path.length >= 5) {
          break;
        }
      }
      return path;
    };

    // Periodically spawn signal pulses
    const pulseInterval = setInterval(() => {
      // Pick one of the hubs (0 or 1)
      const hubId = Math.random() > 0.5 ? 0 : 1;
      const path = findPathToLeaf(hubId);
      if (path.length > 1) {
        activePulses.push({
          path,
          currentEdgeIndex: 0,
          progress: 0,
          speed: 0.015 + Math.random() * 0.01, // speed of traversal per frame
        });
      }
    }, 3500);

    // Gradient helper based on distance from the hub
    const getNodeColors = (node: Node) => {
      if (node.isWarning) {
        return {
          core: node.warningColor || "#EF4444",
          glow: `${node.warningColor || "#EF4444"}33`,
          border: node.warningColor || "#EF4444",
          opacity: 0.9,
        };
      }

      // Calculate distance to closest hub in relative space
      const distToHub0 = Math.hypot(node.relX - 0.22, node.relY - 0.45);
      const distToHub1 = Math.hypot(node.relX - 0.38, node.relY - 0.62);
      const minDist = Math.min(distToHub0, distToHub1);

      // Interpolate colors: Hub is bright purple/indigo, mid is blue, outer is dark blue/faded
      let coreColor = "#6D5EF0";
      let glowColor = "rgba(109, 94, 240, 0.4)";
      let borderColor = "#6D5EF0";
      let opacity = 0.85;

      if (node.type === "hub") {
        coreColor = "#A78BFA";
        glowColor = "rgba(167, 139, 250, 0.6)";
        borderColor = "#8B5CF6";
        opacity = 1.0;
      } else if (minDist < 0.15) {
        // Close to hub -> Bright Purple
        coreColor = "#8B5CF6";
        glowColor = "rgba(139, 92, 246, 0.35)";
        borderColor = "#7C3AED";
        opacity = 0.85;
      } else if (minDist < 0.35) {
        // Mid-distance -> Purple-Blue
        coreColor = "#4F46E5";
        glowColor = "rgba(79, 70, 229, 0.25)";
        borderColor = "#3F37C9";
        opacity = 0.75;
      } else if (minDist < 0.55) {
        // Far -> Bright Blue
        coreColor = "#3B82F6";
        glowColor = "rgba(59, 130, 246, 0.2)";
        borderColor = "#2563EB";
        opacity = 0.6;
      } else {
        // Outer peripheral -> Deep blue/indigo fading out
        coreColor = "#1D4ED8";
        glowColor = "rgba(29, 78, 216, 0.1)";
        borderColor = "#1E3A8A";
        opacity = 0.35;
      }

      return { core: coreColor, glow: glowColor, border: borderColor, opacity };
    };

    // Animation Loop
    let time = 0;
    const animate = () => {
      time += 1;
      ctx.fillStyle = "#05050A";
      ctx.fillRect(0, 0, width, height);

      // 1. Update node drifting positions
      nodes.forEach((node) => {
        const driftX =
          Math.sin(time * node.driftSpeed + node.phaseX) * node.driftRange;
        const driftY =
          Math.cos(time * node.driftSpeed * 0.9 + node.phaseY) *
          node.driftRange;
        node.x = node.baseX + driftX;
        node.y = node.baseY + driftY;
      });

      // 2. Draw Edges (Lines) with glowing layers
      ctx.lineWidth = 1;
      nodes.forEach((node) => {
        node.connections.forEach((connId) => {
          // Draw each connection once
          if (node.id < connId) {
            const target = nodes[connId];
            const colorA = getNodeColors(node);
            const colorB = getNodeColors(target);

            // Edge gradient
            const edgeGrad = ctx.createLinearGradient(
              node.x,
              node.y,
              target.x,
              target.y,
            );
            edgeGrad.addColorStop(0, colorA.core);
            edgeGrad.addColorStop(1, colorB.core);

            const avgOpacity = (colorA.opacity + colorB.opacity) / 2;

            // Draw soft outer glow of line
            ctx.beginPath();
            ctx.moveTo(node.x, node.y);
            ctx.lineTo(target.x, target.y);
            ctx.strokeStyle = edgeGrad;
            ctx.globalAlpha = avgOpacity * 0.12;
            ctx.lineWidth = 3.5;
            ctx.stroke();

            // Draw core crisp line
            ctx.globalAlpha = avgOpacity * 0.35;
            ctx.lineWidth = 0.75;
            ctx.stroke();
          }
        });
      });
      ctx.globalAlpha = 1.0; // Reset alpha

      // 3. Draw Nodes with glow circles
      nodes.forEach((node) => {
        const { core, glow, border, opacity } = getNodeColors(node);

        // Soft outer glow circle
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius * 2.2, 0, Math.PI * 2);
        ctx.fillStyle = glow;
        ctx.globalAlpha = opacity * 0.5;
        ctx.fill();

        // Core circle
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
        ctx.fillStyle = core;
        ctx.globalAlpha = opacity;
        ctx.fill();

        // Node border
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
        ctx.strokeStyle = border;
        ctx.globalAlpha = opacity;
        ctx.lineWidth = 1;
        ctx.stroke();
      });
      ctx.globalAlpha = 1.0; // Reset alpha

      // 4. Update and Draw Signal Pulses
      for (let i = activePulses.length - 1; i >= 0; i--) {
        const pulse = activePulses[i];
        const { path, currentEdgeIndex, progress, speed } = pulse;

        const nodeA = nodes[path[currentEdgeIndex]];
        const nodeB = nodes[path[currentEdgeIndex + 1]];

        if (!nodeA || !nodeB) {
          activePulses.splice(i, 1);
          continue;
        }

        // Interpolate current position of the pulse along the edge
        const px = nodeA.x + (nodeB.x - nodeA.x) * progress;
        const py = nodeA.y + (nodeB.y - nodeA.y) * progress;

        // Draw propagating pulse particle
        // Outer glow
        const pulseGlow = ctx.createRadialGradient(px, py, 1, px, py, 8);
        pulseGlow.addColorStop(0, "#FFFFFF");
        pulseGlow.addColorStop(0.3, "rgba(167, 139, 250, 0.8)");
        pulseGlow.addColorStop(1, "rgba(109, 94, 240, 0)");

        ctx.beginPath();
        ctx.arc(px, py, 9, 0, Math.PI * 2);
        ctx.fillStyle = pulseGlow;
        ctx.fill();

        // Inner core
        ctx.beginPath();
        ctx.arc(px, py, 2.5, 0, Math.PI * 2);
        ctx.fillStyle = "#FFFFFF";
        ctx.fill();

        // Progress pulse along the path
        pulse.progress += speed;
        if (pulse.progress >= 1) {
          pulse.progress = 0;
          pulse.currentEdgeIndex += 1;

          // If reached the end of the path (leaf node), remove it
          if (pulse.currentEdgeIndex >= path.length - 1) {
            activePulses.splice(i, 1);
          }
        }
      }

      animationFrameId = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener("resize", updatePositions);
      clearInterval(pulseInterval);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 w-full h-full block pointer-events-none z-0 dependency-graph-canvas"
    />
  );
};
