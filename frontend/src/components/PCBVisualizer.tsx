import React, { useEffect, useRef } from 'react';

interface PlacedComponent {
  ref: string;
  x: number;
  y: number;
  rotation: number;
  w: number;
  h: number;
}

interface Trace {
  net_name: string;
  path_points: [number, number][];
  width_mm: number;
}

interface Unrouted {
  net: string;
  p1: [number, number];
  p2: [number, number];
}

interface PCBVisualizerProps {
  widthMm: number;
  heightMm: number;
  placements: PlacedComponent[];
  traces: Trace[];
  unrouted: Unrouted[];
}

const PCBVisualizer: React.FC<PCBVisualizerProps> = ({ widthMm, heightMm, placements, traces, unrouted }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear and set background (Dark Green Solder Mask)
    ctx.fillStyle = '#0a3d0a';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    const scale = canvas.width / widthMm;

    // 1. Draw Traces (Copper)
    ctx.strokeStyle = '#c0c0c0'; // Silver/Nickel color for traces
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';

    traces.forEach(trace => {
      if (trace.path_points.length < 2) return;
      ctx.lineWidth = trace.width_mm * scale;
      ctx.beginPath();
      ctx.moveTo(trace.path_points[0][0] * scale, trace.path_points[0][1] * scale);
      for (let i = 1; i < trace.path_points.length; i++) {
        ctx.lineTo(trace.path_points[i][0] * scale, trace.path_points[i][1] * scale);
      }
      ctx.stroke();
    });

    // 2. Draw Ratsnest (Unrouted)
    ctx.setLineDash([5, 5]);
    ctx.strokeStyle = '#ffff00'; // Yellow for unrouted
    ctx.lineWidth = 1;
    if (Array.isArray(unrouted)) {
      unrouted.forEach(u => {
        // Backend might send string IDs instead of coordinate pairs; skip drawing them to prevent crashes
        if (typeof u === 'string' || !u.p1 || !u.p2) return;
        
        ctx.beginPath();
        ctx.moveTo(u.p1[0] * scale, u.p1[1] * scale);
        ctx.lineTo(u.p2[0] * scale, u.p2[1] * scale);
        ctx.stroke();
      });
    }
    ctx.setLineDash([]);

    // 3. Draw Components
    ctx.fillStyle = '#1a1a1a'; // Black component body
    ctx.strokeStyle = '#ffffff'; // White silkscreen
    ctx.lineWidth = 1;

    placements.forEach(p => {
      const w = p.w * scale;
      const h = p.h * scale;

      ctx.save();
      ctx.translate(p.x * scale, p.y * scale);
      ctx.rotate((p.rotation * Math.PI) / 180);
      
      // Draw Body
      ctx.fillRect(-w / 2, -h / 2, w, h);
      ctx.strokeRect(-w / 2, -h / 2, w, h);

      // Draw Reference
      ctx.fillStyle = '#ffffff';
      ctx.font = `${Math.max(8, 2 * scale)}px Inter`;
      ctx.textAlign = 'center';
      ctx.fillText(p.ref, 0, 0);
      
      ctx.restore();
    });

  }, [widthMm, heightMm, placements, traces]);

  return (
    <div className="pcb-visualizer-container" style={{ margin: '20px 0', borderRadius: '8px', overflow: 'hidden', border: '1px solid #333' }}>
      <canvas 
        ref={canvasRef} 
        width={widthMm * 5} // High resolution internal coords
        height={heightMm * 5}
        style={{ width: '100%', height: 'auto', display: 'block' }}
      />
    </div>
  );
};

export default PCBVisualizer;
