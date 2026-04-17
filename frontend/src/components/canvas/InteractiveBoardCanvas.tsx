import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Trash2 } from 'lucide-react';

interface Component {
  id: string;
  x: number;
  y: number;
  w: number;
  h: number;
  ref: string;
  color: string;
}

interface BoardState {
  components: Component[];
  traces: { x1: number; y1: number; x2: number; y2: number }[];
}

const WS_URL = 'ws://localhost:8000/api/v1/workspace/demo-project/ws';

const InteractiveBoardCanvas: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const [boardState, setBoardState] = useState<BoardState>({
    components: [
      { id: 'U1', x: 100, y: 100, w: 60, h: 40, ref: 'MCU', color: '#312e81' },
      { id: 'D1', x: 250, y: 180, w: 30, h: 18, ref: 'LED', color: '#065f46' },
      { id: 'R1', x: 180, y: 250, w: 40, h: 20, ref: 'R 10k', color: '#7c2d12' },
    ],
    traces: [
      { x1: 160, y1: 120, x2: 250, y2: 189 },
      { x1: 160, y1: 130, x2: 180, y2: 260 },
    ]
  });

  const [dragging, setDragging] = useState<{ id: string; offX: number; offY: number } | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // WebSocket connection
  useEffect(() => {
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => console.log('[WS] Connected to workspace');
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === 'init' || msg.type === 'update') {
        setBoardState(prev => ({
          ...prev,
          components: msg.state.components ?? prev.components,
          traces: msg.state.traces ?? prev.traces
        }));
      }
    };
    ws.onerror = () => console.warn('[WS] Backend not available, running in local-only mode.');
    ws.onclose = () => console.log('[WS] Disconnected');

    return () => ws.close();
  }, []);

  // Canvas draw
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Background
    ctx.fillStyle = '#0a100a';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Grid
    ctx.strokeStyle = '#141f14';
    ctx.lineWidth = 1;
    for (let i = 0; i < canvas.width; i += 20) {
      ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i, canvas.height); ctx.stroke();
    }
    for (let i = 0; i < canvas.height; i += 20) {
      ctx.beginPath(); ctx.moveTo(0, i); ctx.lineTo(canvas.width, i); ctx.stroke();
    }

    // Traces (copper)
    ctx.strokeStyle = '#a3a37a';
    ctx.lineWidth = 2.5;
    ctx.lineCap = 'round';
    boardState.traces.forEach(t => {
      ctx.beginPath();
      ctx.moveTo(t.x1, t.y1);
      ctx.lineTo(t.x2, t.y2);
      ctx.stroke();
    });

    // Components
    boardState.components.forEach(c => {
      const isSelected = c.id === selectedId;

      // Glow effect for selected
      if (isSelected) {
        ctx.shadowColor = '#38bdf8';
        ctx.shadowBlur = 14;
      } else {
        ctx.shadowBlur = 0;
      }

      // Body
      ctx.fillStyle = c.color;
      ctx.strokeStyle = isSelected ? '#38bdf8' : '#4a5568';
      ctx.lineWidth = isSelected ? 2 : 1;
      ctx.beginPath();
      ctx.roundRect(c.x, c.y, c.w, c.h, 4);
      ctx.fill();
      ctx.stroke();

      // Component Ref label
      ctx.shadowBlur = 0;
      ctx.fillStyle = '#e2e8f0';
      ctx.font = `bold ${Math.max(9, Math.min(13, c.w / 4))}px Inter, sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(c.ref, c.x + c.w / 2, c.y + c.h / 2);
    });

    ctx.shadowBlur = 0;
  }, [boardState, selectedId]);

  const getHitComponent = useCallback((x: number, y: number) => {
    // Reverse order so top-rendered items get priority
    for (let i = boardState.components.length - 1; i >= 0; i--) {
      const c = boardState.components[i];
      if (x >= c.x && x <= c.x + c.w && y >= c.y && y <= c.y + c.h) return c;
    }
    return null;
  }, [boardState.components]);

  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const r = canvasRef.current!.getBoundingClientRect();
    const x = e.clientX - r.left;
    const y = e.clientY - r.top;
    const hit = getHitComponent(x, y);
    if (hit) {
      setSelectedId(hit.id);
      setDragging({ id: hit.id, offX: x - hit.x, offY: y - hit.y });
    } else {
      setSelectedId(null);
    }
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!dragging) return;
    const r = canvasRef.current!.getBoundingClientRect();
    const nx = e.clientX - r.left - dragging.offX;
    const ny = e.clientY - r.top - dragging.offY;

    setBoardState(prev => ({
      ...prev,
      components: prev.components.map(c =>
        c.id === dragging.id ? { ...c, x: nx, y: ny } : c
      )
    }));
  };

  const handleMouseUp = () => {
    if (dragging && wsRef.current?.readyState === WebSocket.OPEN) {
      const comp = boardState.components.find(c => c.id === dragging.id);
      if (comp) {
        wsRef.current.send(JSON.stringify({
          type: 'component_move',
          component_id: comp.id,
          x: comp.x,
          y: comp.y,
        }));
      }
    }
    setDragging(null);
  };

  const handleClearCanvas = () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'clear_canvas' }));
    } else {
      setBoardState({ components: [], traces: [] });
    }
  };

  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#09090b', overflow: 'auto', position: 'relative' }}>
      <canvas
        ref={canvasRef}
        width={900}
        height={650}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        style={{
          cursor: dragging ? 'grabbing' : 'grab',
          border: '1px solid #27272a',
          borderRadius: '8px',
          boxShadow: '0 0 40px rgba(0,0,0,0.7)',
        }}
      />
      <button 
        onClick={handleClearCanvas}
        style={{
          position: 'absolute',
          top: '16px',
          right: '16px',
          background: 'var(--bg-panel)',
          border: '1px solid var(--border-color)',
          color: 'var(--text-secondary)',
          padding: '6px 12px',
          borderRadius: '6px',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          fontSize: '12px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.5)',
          transition: 'all 0.2s',
          zIndex: 10
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.color = '#ef4444';
          e.currentTarget.style.borderColor = '#ef4444';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.color = 'var(--text-secondary)';
          e.currentTarget.style.borderColor = 'var(--border-color)';
        }}
      >
        <Trash2 size={14} /> Clear Canvas
      </button>
    </div>
  );
};

export default InteractiveBoardCanvas;
