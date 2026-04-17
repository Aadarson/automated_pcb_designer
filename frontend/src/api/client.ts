import type { PCBDesignRequest, PCBDesignResponse } from '../types/design';

export const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const getHeaders = () => {
    const token = localStorage.getItem("token");
    return {
        "Content-Type": "application/json",
        ...(token ? { "Authorization": `Bearer ${token}` } : {})
    };
};

export const postDesign = async (req: PCBDesignRequest): Promise<PCBDesignResponse> => {
    const res = await fetch(`${API_BASE}/api/v1/design/`, {
        method: "POST",
        headers: getHeaders(),
        body: JSON.stringify(req)
    });
    if (!res.ok) throw new Error("Failed to post design");
    return res.json();
};

export const getDesignStatus = async (jobId: string): Promise<PCBDesignResponse> => {
    const res = await fetch(`${API_BASE}/api/v1/design/${jobId}`, {
        headers: getHeaders()
    });
    if (!res.ok) throw new Error("Failed to get design status");
    return res.json();
};

export const openDesignSocket = (jobId: string): WebSocket => {
    const wsUrl = API_BASE.replace("http", "ws") + `/api/v1/design/${jobId}/ws`;
    return new WebSocket(wsUrl);
};
