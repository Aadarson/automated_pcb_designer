import React from 'react';
import { API_BASE } from '../api/client';

export const ExportPanel: React.FC<{ result: any }> = ({ result }) => {
    if (!result) return null;

    return (
        <div className="export-panel">
            <h3>Export Options</h3>
            <div className="export-links" style={{ marginTop: '15px', display: 'flex', gap: '10px' }}>
                {result.pcb_file && (
                    <a 
                        href={`${API_BASE}${result.pcb_file}`} 
                        download 
                        className="btn-primary"
                        style={{ padding: '8px 16px', backgroundColor: '#3b82f6', color: 'white', borderRadius: '4px', textDecoration: 'none' }}
                    >
                        Download PCB
                    </a>
                )}
                {result.zip_file && (
                    <a 
                        href={`${API_BASE}${result.zip_file}`} 
                        download 
                        className="btn-secondary"
                        style={{ padding: '8px 16px', backgroundColor: '#6b7280', color: 'white', borderRadius: '4px', textDecoration: 'none' }}
                    >
                        Download Full Project (ZIP)
                    </a>
                )}
                {result.gerber_file && (
                    <a 
                        href={`${API_BASE}${result.gerber_file}`} 
                        download 
                        className="btn-success"
                        style={{ padding: '8px 16px', backgroundColor: '#10b981', color: 'white', borderRadius: '4px', textDecoration: 'none' }}
                    >
                        Download Gerbers (ZIP)
                    </a>
                )}
            </div>

            <div className="drc-summary" style={{ marginTop: '20px' }}>
                <h4>DRC Report</h4>
                {result.drc_report?.passed ? (
                    <p style={{ color: 'green' }}>✓ DRC Passed</p>
                ) : (
                    <div>
                        <p style={{ color: 'orange' }}>⚠ DRC Violations: {result.drc_report?.violations?.length}</p>
                        <ul style={{ fontSize: '0.8rem', color: '#999' }}>
                            {result.drc_report?.violations?.slice(0, 5).map((v: any, i: number) => (
                                <li key={i}>{v.description}</li>
                            ))}
                        </ul>
                    </div>
                )}
            </div>
        </div>
    );
};
