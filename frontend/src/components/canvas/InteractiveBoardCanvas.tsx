import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Trash2, ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';

// ─── Types ────────────────────────────────────────────────────────────────────

interface CanvasComponent {
  id: string;
  ref: string;
  type: string;
  value: string;
  x: number;
  y: number;
  w: number;
  h: number;
  color: string;
  pins: string[];
  footprint: string;
}

interface Trace {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  net: string;
}

interface Connection {
  from: string;
  to: string;
  net: string;
}

interface BoardState {
  components: CanvasComponent[];
  traces: Trace[];
  connections: Connection[];
}

// ─── Constants ────────────────────────────────────────────────────────────────

const WS_URL = 'ws://localhost:8000/api/v1/workspace/demo-project/ws';

const NET_COLORS: Record<string, string> = {
  VCC:  '#f59e0b',   // amber  — power rail
  GND:  '#6b7280',   // gray   — ground
};

const getNetColor = (net: string): string => {
  if (net === 'VCC') return NET_COLORS.VCC;
  if (net === 'GND') return NET_COLORS.GND;
  return '#38bdf8'; // sky-blue for signal nets
};

// ─── Component ────────────────────────────────────────────────────────────────

const InteractiveBoardCanvas: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const stateRef = useRef<BoardState>({ components: [], traces: [], connections: [] });

  const [boardState, setBoardState] = useState<BoardState>({
    components: [], traces: [], connections: [],
  });
  const [dragging, setDragging] = useState<{ id: string; offX: number; offY: number } | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1.0);
  const [wsStatus, setWsStatus] = useState<'connecting' | 'connected' | 'offline'>('connecting');

  // Keep ref in sync so canvas draw always has fresh data
  useEffect(() => { stateRef.current = boardState; }, [boardState]);

  // ── WebSocket ──────────────────────────────────────────────────────────────
  useEffect(() => {
    const connect = () => {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        setWsStatus('connected');
        console.log('[Canvas WS] Connected');
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === 'init' || msg.type === 'update') {
            const incoming: BoardState = {
              components:  msg.state.components  ?? [],
              traces:      msg.state.traces      ?? [],
              connections: msg.state.connections ?? [],
            };
            setBoardState(incoming);
          }
        } catch (e) {
          console.error('[Canvas WS] Parse error:', e);
        }
      };

      ws.onerror = () => {
        setWsStatus('offline');
        console.warn('[Canvas WS] Backend unreachable — demo mode.');
      };

      ws.onclose = () => {
        setWsStatus('offline');
        // Attempt reconnect after 3 s
        setTimeout(connect, 3000);
      };
    };

    connect();
    return () => wsRef.current?.close();
  }, []);

  // ── Canvas Draw ────────────────────────────────────────────────────────────
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const { components, traces } = boardState;
    const dpr = window.devicePixelRatio || 1;

    ctx.save();
    ctx.setTransform(zoom * dpr, 0, 0, zoom * dpr, 0, 0);

    const logicalW = canvas.width  / (zoom * dpr);
    const logicalH = canvas.height / (zoom * dpr);

    // Background
    ctx.fillStyle = '#080e08';
    ctx.fillRect(0, 0, logicalW, logicalH);

    // Grid dots
    ctx.fillStyle = '#162016';
    const gridStep = 20;
    for (let gx = 0; gx < logicalW; gx += gridStep) {
      for (let gy = 0; gy < logicalH; gy += gridStep) {
        ctx.fillRect(gx, gy, 1, 1);
      }
    }

    // Board outline
    ctx.strokeStyle = '#22c55e22';
    ctx.lineWidth = 1.5;
    ctx.strokeRect(40, 30, logicalW - 80, logicalH - 60);

    // Traces / copper
    traces.forEach(t => {
      const col = getNetColor(t.net);
      ctx.strokeStyle = col;
      ctx.lineWidth = 2.5;
      ctx.lineCap = 'round';
      ctx.shadowColor = col;
      ctx.shadowBlur = 6;
      ctx.beginPath();
      ctx.moveTo(t.x1, t.y1);

      // Route with a single 45° bend
      const midX = (t.x1 + t.x2) / 2;
      ctx.lineTo(midX, t.y1);
      ctx.lineTo(midX, t.y2);
      ctx.lineTo(t.x2, t.y2);
      ctx.stroke();

      // Pad circles at endpoints
      ctx.shadowBlur = 0;
      ctx.fillStyle = col;
      ctx.beginPath(); ctx.arc(t.x1, t.y1, 3.5, 0, Math.PI * 2); ctx.fill();
      ctx.beginPath(); ctx.arc(t.x2, t.y2, 3.5, 0, Math.PI * 2); ctx.fill();
    });

    ctx.shadowBlur = 0;

    // Components
    components.forEach(c => {
      const isSelected = c.id === selectedId;

      // Selection glow
      if (isSelected) { ctx.shadowColor = '#38bdf8'; ctx.shadowBlur = 18; }
      else             { ctx.shadowBlur = 0; }

      // Body
      const grad = ctx.createLinearGradient(c.x, c.y, c.x, c.y + c.h);
      grad.addColorStop(0, lighten(c.color, 20));
      grad.addColorStop(1, c.color);
      ctx.fillStyle = grad;
      ctx.strokeStyle = isSelected ? '#38bdf8' : '#475569';
      ctx.lineWidth = isSelected ? 2 : 1;
      ctx.beginPath();
      ctx.roundRect(c.x, c.y, c.w, c.h, 5);
      ctx.fill();
      ctx.stroke();

      // Silkscreen-style pin markers (small dots on left edge)
      ctx.shadowBlur = 0;
      ctx.fillStyle = '#94a3b8';
      const pinCount = Math.min(c.pins.length, 6);
      const pinSpacing = c.h / (pinCount + 1);
      for (let i = 0; i < pinCount; i++) {
        ctx.beginPath();
        ctx.arc(c.x + 4, c.y + pinSpacing * (i + 1), 2, 0, Math.PI * 2);
        ctx.fill();
      }

      // Ref label
      ctx.shadowBlur = 0;
      ctx.fillStyle = '#f1f5f9';
      const fontSize = Math.max(8, Math.min(12, c.w / 5));
      ctx.font = `bold ${fontSize}px "Inter", monospace`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(c.ref, c.x + c.w / 2, c.y + c.h / 2 - 5);

      // Value label (smaller)
      ctx.fillStyle = '#94a3b8';
      ctx.font = `${Math.max(7, fontSize - 3)}px "Inter", monospace`;
      ctx.fillText(c.value, c.x + c.w / 2, c.y + c.h / 2 + 7);
    });

    ctx.shadowBlur = 0;
    ctx.restore();
  }, [boardState, selectedId, zoom]);

  // ── Hit Detection ──────────────────────────────────────────────────────────
  const getHitComponent = useCallback((x: number, y: number): CanvasComponent | null => {
    const comps = stateRef.current.components;
    for (let i = comps.length - 1; i >= 0; i--) {
      const c = comps[i];
      if (x >= c.x && x <= c.x + c.w && y >= c.y && y <= c.y + c.h) return c;
    }
    return null;
  }, []);

  const toLogical = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const r = canvasRef.current!.getBoundingClientRect();
    return {
      x: (e.clientX - r.left) / zoom,
      y: (e.clientY - r.top)  / zoom,
    };
  };

  // ── Mouse Handlers ─────────────────────────────────────────────────────────
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const { x, y } = toLogical(e);
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
    const { x, y } = toLogical(e);
    const nx = x - dragging.offX;
    const ny = y - dragging.offY;

    setBoardState(prev => {
      const components = prev.components.map(c =>
        c.id === dragging.id ? { ...c, x: nx, y: ny } : c
      );
      // Recompute traces live while dragging
      const traces = recomputeTraces(components, prev.connections);
      return { ...prev, components, traces };
    });
  };

  const handleMouseUp = () => {
    if (dragging && wsRef.current?.readyState === WebSocket.OPEN) {
      const comp = stateRef.current.components.find(c => c.id === dragging.id);
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
      setBoardState({ components: [], traces: [], connections: [] });
    }
  };

  // ── Zoom ───────────────────────────────────────────────────────────────────
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    setZoom(z => Math.max(0.4, Math.min(3.0, z - e.deltaY * 0.001)));
  };

  // ── Render ─────────────────────────────────────────────────────────────────
  const selected = boardState.components.find(c => c.id === selectedId);

  return (
    <div
      style={{
        width: '100%', height: '100%', display: 'flex', alignItems: 'center',
        justifyContent: 'center', background: '#09090b', overflow: 'hidden',
        position: 'relative',
      }}
    >
      <canvas
        ref={canvasRef}
        width={900}
        height={650}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onWheel={handleWheel}
        style={{
          cursor: dragging ? 'grabbing' : 'grab',
          border: '1px solid #27272a',
          borderRadius: '8px',
          boxShadow: '0 0 60px rgba(0,0,0,0.8)',
        }}
      />

      {/* Top-right toolbar */}
      <div style={{ position: 'absolute', top: 16, right: 16, display: 'flex', gap: 8, flexDirection: 'column' }}>
        {/* WS status badge */}
        <div style={{
          padding: '4px 10px', borderRadius: 999, fontSize: 10, fontWeight: 600,
          background: wsStatus === 'connected' ? '#052e16' : '#1c1917',
          color:      wsStatus === 'connected' ? '#22c55e'  : '#a8a29e',
          border:     `1px solid ${wsStatus === 'connected' ? '#166534' : '#44403c'}`,
          textAlign: 'center',
        }}>
          {wsStatus === 'connected' ? '● LIVE' : wsStatus === 'connecting' ? '○ Connecting…' : '○ Offline'}
        </div>

        <ToolButton onClick={() => setZoom(z => Math.min(3, z + 0.15))} title="Zoom In">
          <ZoomIn size={14} />
        </ToolButton>
        <ToolButton onClick={() => setZoom(z => Math.max(0.4, z - 0.15))} title="Zoom Out">
          <ZoomOut size={14} />
        </ToolButton>
        <ToolButton onClick={() => setZoom(1.0)} title="Reset Zoom">
          <Maximize2 size={14} />
        </ToolButton>
        <ToolButton
          onClick={handleClearCanvas}
          title="Clear Canvas"
          danger
        >
          <Trash2 size={14} />
        </ToolButton>
      </div>

      {/* Component info panel (bottom-left) */}
      {selected && (
        <div style={{
          position: 'absolute', bottom: 20, left: 20,
          background: '#0f172a', border: '1px solid #1e293b',
          borderRadius: 8, padding: '10px 14px', fontSize: 12,
          color: '#94a3b8', minWidth: 180,
          boxShadow: '0 4px 20px rgba(0,0,0,0.6)',
        }}>
          <div style={{ color: '#f1f5f9', fontWeight: 700, marginBottom: 4 }}>
            {selected.ref} — {selected.type}
          </div>
          <div>Value: <span style={{ color: '#38bdf8' }}>{selected.value}</span></div>
          <div>Footprint: <span style={{ color: '#a78bfa', fontSize: 10 }}>{selected.footprint}</span></div>
          <div>Pins: {selected.pins.join(', ')}</div>
          <div style={{ marginTop: 4 }}>
            X: {Math.round(selected.x)} Y: {Math.round(selected.y)}
          </div>
        </div>
      )}

      {/* Zoom indicator */}
      <div style={{
        position: 'absolute', bottom: 20, right: 20,
        fontSize: 11, color: '#52525b', background: '#18181b',
        padding: '4px 8px', borderRadius: 6, border: '1px solid #27272a',
      }}>
        {Math.round(zoom * 100)}%
      </div>
    </div>
  );
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function recomputeTraces(components: CanvasComponent[], connections: Connection[]): Trace[] {
  const pos = Object.fromEntries(components.map(c => [c.id, c]));
  return connections.reduce<Trace[]>((acc, conn) => {
    const src = pos[conn.from.split('.')[0]];
    const dst = pos[conn.to.split('.')[0]];
    if (src && dst) {
      acc.push({
        x1: src.x + src.w / 2,
        y1: src.y + src.h / 2,
        x2: dst.x + dst.w / 2,
        y2: dst.y + dst.h / 2,
        net: conn.net,
      });
    }
    return acc;
  }, []);
}

function lighten(hex: string, amount: number): string {
  const num = parseInt(hex.replace('#', ''), 16);
  const r = Math.min(255, ((num >> 16) & 0xff) + amount);
  const g = Math.min(255, ((num >>  8) & 0xff) + amount);
  const b = Math.min(255,  (num        & 0xff) + amount);
  return `#${((r << 16) | (g << 8) | b).toString(16).padStart(6, '0')}`;
}

interface ToolButtonProps {
  children: React.ReactNode;
  onClick: () => void;
  title?: string;
  danger?: boolean;
}

const ToolButton: React.FC<ToolButtonProps> = ({ children, onClick, title, danger }) => (
  <button
    onClick={onClick}
    title={title}
    style={{
      background: '#18181b', border: '1px solid #27272a',
      color: danger ? '#ef4444' : '#a1a1aa',
      borderColor: danger ? '#7f1d1d' : '#27272a',
      padding: '7px', borderRadius: 6, cursor: 'pointer',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      boxShadow: '0 2px 8px rgba(0,0,0,0.5)',
      transition: 'all 0.15s',
    }}
    onMouseEnter={e => {
      e.currentTarget.style.background = danger ? '#7f1d1d' : '#27272a';
      e.currentTarget.style.color = danger ? '#fca5a5' : '#f1f5f9';
    }}
    onMouseLeave={e => {
      e.currentTarget.style.background = '#18181b';
      e.currentTarget.style.color = danger ? '#ef4444' : '#a1a1aa';
    }}
  >
    {children}
  </button>
);

export default InteractiveBoardCanvas;
