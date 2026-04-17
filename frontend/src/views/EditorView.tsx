import React, { useState } from 'react';
import { Zap, Settings, Download } from 'lucide-react';
import CopilotSidebar from '../components/copilot/CopilotSidebar';
import SchematicCanvas from '../components/canvas/SchematicCanvas';
import InteractiveBoardCanvas from '../components/canvas/InteractiveBoardCanvas';

type ViewMode = 'schematic' | 'pcb';

const EditorView: React.FC = () => {
  const [viewMode, setViewMode] = useState<ViewMode>('pcb');

  return (
    <div className="editor-layout">
      {/* Left Sidebar - AI Copilot */}
      <div className="sidebar-left">
        <CopilotSidebar projectId="demo-project" />
      </div>

      {/* Center - Workspace Canvas */}
      <div className="workspace-center">
        <div className="top-bar">
          <div className="brand-title">
            <Zap size={18} color="#38bdf8" />
            <span>FluxPCB Copilot</span>
          </div>

          <div className="view-tabs">
            <button
              className={`view-tab ${viewMode === 'schematic' ? 'active' : ''}`}
              onClick={() => setViewMode('schematic')}
            >
              Schematic
            </button>
            <button
              className={`view-tab ${viewMode === 'pcb' ? 'active' : ''}`}
              onClick={() => setViewMode('pcb')}
            >
              PCB Layout
            </button>
          </div>

          <button style={{ background: 'transparent', border: '1px solid var(--border-color)', padding: '6px 14px', fontSize: '12px', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', borderRadius: '6px' }}>
            <Download size={14} /> Export
          </button>
        </div>

        <div className="canvas-container">
          {viewMode === 'schematic' && <SchematicCanvas />}
          {viewMode === 'pcb' && <InteractiveBoardCanvas />}
        </div>
      </div>

      {/* Right Sidebar - Properties */}
      <div className="sidebar-right">
        <div className="copilot-header" style={{ fontSize: '13px' }}>
          <Settings size={16} /> Properties
        </div>
        <div style={{ padding: '16px', color: 'var(--text-muted)', fontSize: '13px' }}>
          Select a component on the canvas to view its properties.
        </div>
        <div style={{ padding: '16px', borderTop: '1px solid var(--border-color)', marginTop: 'auto' }}>
          <p style={{ color: 'var(--text-muted)', fontSize: '11px', margin: 0 }}>FluxPCB v0.1 · AI-Powered PCB IDE</p>
        </div>
      </div>
    </div>
  );
};

export default EditorView;
