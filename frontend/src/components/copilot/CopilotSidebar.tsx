import React, { useState, useEffect, useRef } from 'react';
import { Bot, Send, Sparkles, Cpu } from 'lucide-react';

interface Message {
  id: string;
  role: 'user' | 'ai';
  text: string;
}

interface CopilotSidebarProps {
  projectId: string;
}

const QUICK_PROMPTS = [
  'Add an ESP32 microcontroller',
  'Add I2C OLED display',
  'Add 555 Timer blinker',
  'Add USB-C power circuit',
];

const CopilotSidebar: React.FC<CopilotSidebarProps> = ({ projectId }) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'ai',
      text: 'Hi! I\'m your PCB design copilot. Describe a circuit and I\'ll place components on the canvas for you.',
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Connect to backend WebSocket
  useEffect(() => {
    const ws = new WebSocket(
      `ws://localhost:8000/api/v1/workspace/${projectId}/ws`
    );
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('[Copilot WS] Connected');
    };

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === 'copilot_response') {
        setIsLoading(false);
        setMessages((prev) => [
          ...prev,
          { id: Date.now().toString(), role: 'ai', text: msg.text },
        ]);
      }
    };

    ws.onerror = () => {
      console.warn('[Copilot WS] Backend not available, running in demo mode.');
    };

    return () => ws.close();
  }, [projectId]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = (text: string) => {
    if (!text.trim()) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      text,
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({ type: 'copilot_prompt', prompt: text })
      );
    } else {
      // Demo mode fallback
      setTimeout(() => {
        setIsLoading(false);
        setMessages((prev) => [
          ...prev,
          {
            id: Date.now().toString(),
            role: 'ai',
            text: `Generating layout for: "${text}"… Component placed on canvas! (Demo mode — start the backend for live AI generation)`,
          },
        ]);
      }, 1200);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  return (
    <div className="copilot-container">
      {/* Header */}
      <div className="copilot-header">
        <Bot size={18} color="#38bdf8" />
        <span>AI Copilot</span>
        <span
          style={{
            marginLeft: 'auto',
            fontSize: '10px',
            color: 'var(--text-muted)',
            background: 'var(--bg-surface)',
            padding: '2px 8px',
            borderRadius: '999px',
          }}
        >
          {projectId}
        </span>
      </div>

      {/* Messages */}
      <div className="copilot-messages">
        {messages.map((msg) => (
          <div key={msg.id} className={`c-message ${msg.role}`}>
            {msg.role === 'ai' && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px', opacity: 0.7 }}>
                <Sparkles size={12} />
                <span style={{ fontSize: '10px', fontWeight: 600, letterSpacing: '0.05em', textTransform: 'uppercase' }}>Copilot</span>
              </div>
            )}
            {msg.text}
          </div>
        ))}

        {/* Loading indicator */}
        {isLoading && (
          <div className="c-message ai" style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
            <span className="dot-pulse" />
            <span style={{ fontSize: '12px', opacity: 0.7 }}>Thinking…</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Quick prompt chips */}
      <div style={{ padding: '8px 16px', display: 'flex', flexWrap: 'wrap', gap: '6px', borderTop: '1px solid var(--border-color)' }}>
        {QUICK_PROMPTS.map((p) => (
          <button
            key={p}
            onClick={() => sendMessage(p)}
            style={{
              background: 'var(--bg-surface)',
              border: '1px solid var(--border-color)',
              color: 'var(--text-secondary)',
              borderRadius: '999px',
              padding: '4px 10px',
              fontSize: '11px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              transition: 'all 0.2s',
            }}
          >
            <Cpu size={10} />
            {p}
          </button>
        ))}
      </div>

      {/* Input */}
      <div className="copilot-input">
        <form onSubmit={handleSubmit}>
          <input
            type="text"
            placeholder="Describe your circuit…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isLoading}
          />
          <button type="submit" disabled={isLoading || !input.trim()}>
            <Send size={16} />
          </button>
        </form>
      </div>
    </div>
  );
};

export default CopilotSidebar;
