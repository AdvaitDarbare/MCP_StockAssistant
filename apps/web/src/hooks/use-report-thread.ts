import { useCallback, useMemo, useState } from 'react';

export interface ReportRunResponse {
    report_type: string;
    title: string;
    generated_at: string;
    markdown: string;
    data?: Record<string, unknown>;
    assumptions?: string[];
    limitations?: string[];
    sources_used?: string[];
    persisted_run_id?: string;
    tool_plan?: Array<{ tool: string; reason: string }>;
    mlflow_run_id?: string;
    generation_ms?: number;
    quality_gate?: {
        score: number;
        checks: Record<string, boolean>;
        warnings: string[];
    };
    orchestration_trace?: Array<{
        phase: string;
        status: string;
        details?: unknown;
    }>;
    effective_prompt?: string;
    thread_id?: string;
    follow_up_supported?: boolean;
    follow_up_question?: string;
}

export interface ReportThreadMessage {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    createdAt: string;
}

export interface ReportRunRequest {
    reportType: string;
    payload: Record<string, unknown>;
    ownerKey: string;
    promptOverride?: string;
    followUpQuestion?: string;
    refreshData?: boolean;
    threadId?: string;
}

export interface ReportFollowupRequest {
    reportType: string;
    ownerKey: string;
    threadId: string;
    question: string;
    refreshData?: boolean;
}

function toMessage(role: 'user' | 'assistant', content: string): ReportThreadMessage {
    return {
        id: `${role}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        role,
        content,
        createdAt: new Date().toISOString(),
    };
}

export function useReportThread() {
    const [currentReport, setCurrentReport] = useState<ReportRunResponse | null>(null);
    const [threadId, setThreadId] = useState<string>('');
    const [messages, setMessages] = useState<ReportThreadMessage[]>([]);
    const [isRunning, setIsRunning] = useState(false);
    const [isFollowingUp, setIsFollowingUp] = useState(false);
    const [error, setError] = useState('');

    const runReport = useCallback(async (request: ReportRunRequest) => {
        setIsRunning(true);
        setError('');
        try {
            const resp = await fetch(`/api/py/reports/${request.reportType}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    payload: request.payload,
                    owner_key: request.ownerKey,
                    prompt_override: request.promptOverride,
                    thread_id: request.threadId,
                    follow_up_question: request.followUpQuestion,
                    refresh_data: Boolean(request.refreshData),
                }),
            });
            const json = await resp.json();
            if (!resp.ok) throw new Error(json.detail || 'Failed to run report');

            setCurrentReport(json);
            if (json.thread_id) setThreadId(String(json.thread_id));
            setMessages((prev) => {
                const next = [...prev];
                if (request.followUpQuestion?.trim()) {
                    next.push(toMessage('user', request.followUpQuestion.trim()));
                }
                next.push(toMessage('assistant', String(json.markdown || '')));
                return next;
            });
            return json as ReportRunResponse;
        } catch (e) {
            const msg = e instanceof Error ? e.message : 'Failed to run report';
            setError(msg);
            throw e;
        } finally {
            setIsRunning(false);
        }
    }, []);

    const followUp = useCallback(async (request: ReportFollowupRequest) => {
        setIsFollowingUp(true);
        setError('');
        try {
            setMessages((prev) => [...prev, toMessage('user', request.question)]);
            const resp = await fetch(`/api/py/reports/${request.reportType}/followup`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    owner_key: request.ownerKey,
                    thread_id: request.threadId,
                    question: request.question,
                    refresh_data: Boolean(request.refreshData),
                }),
            });
            const json = await resp.json();
            if (!resp.ok) throw new Error(json.detail || 'Failed to run follow-up');
            setCurrentReport(json);
            setMessages((prev) => [...prev, toMessage('assistant', String(json.markdown || ''))]);
            return json as ReportRunResponse;
        } catch (e) {
            const msg = e instanceof Error ? e.message : 'Failed to run follow-up';
            setError(msg);
            throw e;
        } finally {
            setIsFollowingUp(false);
        }
    }, []);

    const resetThread = useCallback(() => {
        setCurrentReport(null);
        setThreadId('');
        setMessages([]);
        setError('');
    }, []);

    const canFollowUp = useMemo(() => Boolean(threadId && currentReport?.follow_up_supported), [threadId, currentReport]);

    return {
        currentReport,
        threadId,
        messages,
        isRunning,
        isFollowingUp,
        error,
        canFollowUp,
        runReport,
        followUp,
        resetThread,
        setMessages,
    };
}
