import React from 'react';

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

interface BoardCanvasProps {
  widthMm: number;
  heightMm: number;
  placements: PlacedComponent[];
  traces: Trace[];
}

export const BoardCanvas: React.FC<BoardCanvasProps> = ({ widthMm, heightMm, placements, traces }) => {
  const scale = 10; // 1mm = 10px original SVG units
  
  return (
    <div className="board-canvas-container" style={{ background: '#1a1a1a', padding: '20px', borderRadius: '12px' }}>
      <svg 
        viewBox={`0 0 ${widthMm * scale} ${heightMm * scale}`}
        style={{ width: '100%', height: 'auto', backgroundColor: '#0a3d0a', borderRadius: '4px' }}
      >
        {/* 1. Traces */}
        {traces.map((trace, i) => (
          <polyline
            key={`trace-${i}`}
            points={trace.path_points.map(p => `${p[0] * scale},${p[1] * scale}`).join(' ')}
            fill="none"
            stroke="#c0c0c0"
            strokeWidth={trace.width_mm * scale}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        ))}

        {/* 2. Components */}
        {placements.map((p, i) => (
          <g key={`comp-${i}`} transform={`translate(${p.x * scale}, ${p.y * scale}) rotate(${p.rotation})`}>
            <rect
              x={-p.w * scale / 2}
              y={-p.h * scale / 2}
              width={p.w * scale}
              height={p.h * scale}
              fill="#333"
              stroke="#fff"
              strokeWidth="2"
            />
            <text
              x="0"
              y="0"
              fill="#fff"
              fontSize={12}
              textAnchor="middle"
              dominantBaseline="middle"
              style={{ pointerEvents: 'none' }}
            >
              {p.ref}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
};
