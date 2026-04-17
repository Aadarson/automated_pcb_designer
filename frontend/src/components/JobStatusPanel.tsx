import React, { useEffect, useState } from 'react';
import { openDesignSocket } from '../api/client';
import { ExportPanel } from './ExportPanel';
import type { PCBDesignResponse } from '../types/design';
import { BoardCanvas } from "./BoardCanvas";

interface JobEvent {
    progress?: number;
    step?: string;
    status?: 'running' | 'complete' | 'error';
    result?: PCBDesignResponse['result'];
    error?: string;
    data?: {
        placements?: any[];
        traces?: any[];
        unrouted?: any[];
    };
}

export const JobStatusPanel: React.FC<{ jobId: string }> = ({ jobId }) => {
    const [progress, setProgress] = useState(0);
    const [step, setStep] = useState('Initializing...');
    const [status, setStatus] = useState<'running'|'complete'|'error'>('running');
    const [resultData, setResultData] = useState<PCBDesignResponse['result']>(undefined);
    const [errorMsg, setErrorMsg] = useState('');
    const [events, setEvents] = useState<JobEvent[]>([]);

    useEffect(() => {
        const ws = openDesignSocket(jobId);
        
        ws.onmessage = (event) => {
            try {
                const data: JobEvent = JSON.parse(event.data);
                setEvents(prev => [...prev, data]);
                
                if (data.progress) setProgress(data.progress);
                if (data.step) setStep(data.step);
                
                if (data.step === 'done' || data.status === 'complete') {
                    setStatus('complete');
                    setResultData(data.result);
                } else if (data.step === 'error' || data.status === 'error') {
                    setStatus('error');
                    setErrorMsg(data.error || 'Unknown error');
                }
            } catch (e) {
                console.error("Failed to parse websocket message", e);
            }
        };

        return () => ws.close();
    }, [jobId]);

    const latestPlacements = [...events].reverse().find(e => e.data?.placements)?.data?.placements || [];
    const latestTraces = [...events].reverse().find(e => e.data?.traces)?.data?.traces || [];
    const latestUnrouted = [...events].reverse().find(e => e.data?.unrouted)?.data?.unrouted || [];

    return (
        <div className="status-panel">
            <h3>Job Status: {jobId}</h3>
            {status === 'running' && (
                <div>
                    <p>Current Step: <strong>{step}</strong></p>
                    <div className="progress-bar">
                        <div className="progress-fill" style={{ width: `${progress}%` }}></div>
                    </div>
                    <span>{progress}%</span>
                </div>
            )}
            
            {(status === 'complete' || status === 'running' || resultData) && resultData && (
                <div className="metrics-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', margin: '15px 0' }}>
                    <div className="metric-card">
                        <span>Placement Score</span>
                        <strong>{((resultData.placement_score || 0) * 100).toFixed(1)}%</strong>
                    </div>
                    <div className="metric-card">
                        <span>Routing Completion</span>
                        <strong>{((resultData.routing_completion || 0) * 100).toFixed(1)}%</strong>
                    </div>
                    {resultData.drc_report && (
                        <div className="metric-card" style={{ gridColumn: 'span 2' }}>
                            <span>DRC Violations</span>
                            <strong style={{ color: (resultData.drc_report.violations?.length || 0) > 0 ? 'red' : 'green' }}>
                                {resultData.drc_report.violations?.length || 0}
                            </strong>
                        </div>
                    )}
                </div>
            )}

            {(status === 'complete' || resultData) && (
                <div>
                    {status === 'complete' && <p style={{ color: 'green', fontWeight: 'bold' }}>Success! Generation Complete.</p>}
                    <ExportPanel result={resultData} />
                </div>
            )}

            {status === 'error' && !resultData && (
                <div>
                    <p style={{ color: 'red' }}>Error during generation:</p>
                    <p>{errorMsg}</p>
                </div>
            )}

            {(latestPlacements.length > 0 || latestTraces.length > 0) && (
                <div style={{ marginTop: '20px' }}>
                    <h4>Layout Preview</h4>
                    <BoardCanvas 
                        widthMm={80} 
                        heightMm={60} 
                        placements={latestPlacements}
                        traces={latestTraces}
                    />
                </div>
            )}
        </div>
    );
};
