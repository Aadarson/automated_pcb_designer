import React, { useState } from 'react';
import { DesignForm } from './components/DesignForm';
import { JobStatusPanel } from './components/JobStatusPanel';
import './App.css';

function App() {
  const [activeJobId, setActiveJobId] = useState<string | null>(null);

  return (
    <div className="App">
      <header className="App-header">
        <h1>Automated PCB Designer</h1>
      </header>
      <main className="App-main" style={{ display: 'flex', gap: '2rem', padding: '2rem' }}>
        <div className="sidebar" style={{ flex: '1' }}>
            <DesignForm onJobStart={setActiveJobId} />
        </div>
        <div className="content" style={{ flex: '2' }}>
            {activeJobId ? (
                <JobStatusPanel jobId={activeJobId} />
            ) : (
                <div className="empty-state">
                    <p>Fill out the form on the left to start a new PCB design job.</p>
                </div>
            )}
        </div>
      </main>
    </div>
  );
}

export default App;
