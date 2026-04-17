import React, { useState } from 'react';
import type { PCBDesignRequest } from '../types/design';
import { postDesign } from '../api/client';

export const DesignForm: React.FC<{ onJobStart: (jobId: string) => void }> = ({ onJobStart }) => {
    const [prompt, setPrompt] = useState('');
    const [projectName, setProjectName] = useState('New Project');
    const [width, setWidth] = useState(80);
    const [height, setHeight] = useState(60);
    const [layers, setLayers] = useState<2|4|6>(2);
    const [fillCopper, setFillCopper] = useState(true);
    const [powerNets, setPowerNets] = useState('VCC, GND');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        
        const req: PCBDesignRequest = {
            prompt,
            project_name: projectName,
            board: {
                width_mm: width,
                height_mm: height,
                layers,
                outline: "rect"
            },
            routing_goals: {
                minimize: ["wire_length"],
                protect_nets: [],
                fill_copper: fillCopper
            }
        };

        try {
            const res = await postDesign(req);
            onJobStart(res.job_id);
        } catch (error) {
            console.error(error);
            alert("Failed to start design job");
        }
    };

    return (
        <form onSubmit={handleSubmit} className="design-form">
            <h2>Describe your PCB</h2>
            <div>
                <label>Project Name:</label>
                <input type="text" value={projectName} onChange={e => setProjectName(e.target.value)} required />
            </div>
            <div>
                <label>Prompt:</label>
                <textarea value={prompt} onChange={e => setPrompt(e.target.value)} rows={4} required placeholder="Describe your circuit..."/>
            </div>
            <div>
                <label>Width (mm):</label>
                <input type="number" value={width} onChange={e => setWidth(Number(e.target.value))} min={1} max={500} required />
            </div>
            <div>
                <label>Height (mm):</label>
                <input type="number" value={height} onChange={e => setHeight(Number(e.target.value))} min={1} max={500} required />
            </div>
            <div>
                <label>Layers:</label>
                <select value={layers} onChange={e => setLayers(Number(e.target.value) as 2|4|6)}>
                    <option value={2}>2</option>
                    <option value={4}>4</option>
                    <option value={6}>6</option>
                </select>
            </div>
            <div>
                <label>
                    <input type="checkbox" checked={fillCopper} onChange={e => setFillCopper(e.target.checked)} />
                    Fill copper on unused areas
                </label>
            </div>
            <div>
                <label>Power Nets (comma separated):</label>
                <input type="text" value={powerNets} onChange={e => setPowerNets(e.target.value)} />
            </div>
            <button type="submit">Generate PCB</button>
        </form>
    );
};
