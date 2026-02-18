import { useState, useCallback, useRef } from 'react';

export interface Message {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    traceLines?: string[];
}

export type AgentStatus =
    | 'planner'
    | 'market_data'
    | 'technical_analysis'
    | 'fundamentals'
    | 'sentiment'
    | 'advisor'
    | 'macro'
    | 'report_generator'
    | 'report_followup'
    | 'idle';

const AGENT_LABELS: Record<AgentStatus, string> = {
    planner: 'Analyzing request...',
    market_data: 'Fetching market data...',
    technical_analysis: 'Running technical indicators...',
    fundamentals: 'Evaluating fundamentals...',
    sentiment: 'Assessing sentiment and flows...',
    advisor: 'Generating investment advice...',
    macro: 'Analyzing economic trends...',
    report_generator: 'Generating report...',
    report_followup: 'Processing follow-up...',
    idle: ''
};

function normalizeStreamContent(content: unknown): string {
    if (typeof content === 'string') return content;
    if (Array.isArray(content)) {
        return content
            .map((item) => {
                if (typeof item === 'string') return item;
                if (item && typeof item === 'object') {
                    const rec = item as Record<string, unknown>;
                    if (typeof rec.text === 'string') return rec.text;
                    if (typeof rec.content === 'string') return rec.content;
                }
                return '';
            })
            .join('');
    }
    if (content && typeof content === 'object') {
        const rec = content as Record<string, unknown>;
        if (typeof rec.text === 'string') return rec.text;
        if (typeof rec.content === 'string') return rec.content;
    }
    return '';
}

function getOrCreateClientId(storageKey: string, prefix: string): string {
    if (typeof window === 'undefined') {
        // For server-side rendering, generate a proper UUID
        return typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : 
               `${Math.random().toString(36).substr(2, 8)}-${Math.random().toString(36).substr(2, 4)}-4${Math.random().toString(36).substr(2, 3)}-${Math.random().toString(36).substr(2, 4)}-${Math.random().toString(36).substr(2, 12)}`;
    }
    try {
        const existing = window.localStorage.getItem(storageKey);
        // Check if existing value has the old prefix format and clean it up
        if (existing) {
            // If it starts with a prefix like 'conv-', 'user-', etc., extract just the UUID part
            if (existing.includes('-') && existing.length > 36) {
                const parts = existing.split('-');
                if (parts.length >= 6) {
                    // Reconstruct proper UUID from the parts (skip the first prefix part)
                    const uuidParts = parts.slice(1);
                    if (uuidParts.length === 5) {
                        const cleanUuid = uuidParts.join('-');
                        // Validate it's a proper UUID format (36 characters)
                        if (cleanUuid.length === 36) {
                            window.localStorage.setItem(storageKey, cleanUuid);
                            return cleanUuid;
                        }
                    }
                }
            }
            // If it's already a proper UUID, return it
            if (existing.length === 36 && existing.match(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i)) {
                return existing;
            }
        }
        
        // Generate a proper UUID (36 characters)
        const generated = typeof crypto !== 'undefined' && crypto.randomUUID ? 
                         crypto.randomUUID() : 
                         `${Math.random().toString(36).substr(2, 8)}-${Math.random().toString(36).substr(2, 4)}-4${Math.random().toString(36).substr(2, 3)}-${Math.random().toString(36).substr(2, 4)}-${Math.random().toString(36).substr(2, 12)}`;
        
        window.localStorage.setItem(storageKey, generated);
        return generated;
    } catch {
        // Fallback to proper UUID format (36 characters)
        return typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : 
               `${Math.random().toString(36).substr(2, 8)}-${Math.random().toString(36).substr(2, 4)}-4${Math.random().toString(36).substr(2, 3)}-${Math.random().toString(36).substr(2, 4)}-${Math.random().toString(36).substr(2, 12)}`;
    }
}

function formatTaskStatus(status: unknown): string {
    const value = String(status || '').toLowerCase();
    if (value === 'completed') return 'completed';
    if (value === 'failed') return 'failed';
    if (value === 'skipped') return 'skipped';
    return 'pending';
}

export function useSupervisorChat() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [activeAgent, setActiveAgent] = useState<AgentStatus>('idle');

    const messagesRef = useRef<Message[]>([]);
    const conversationIdRef = useRef<string>(getOrCreateClientId('asa_conversation_id_v2', 'conv'));
    const userIdRef = useRef<string>(getOrCreateClientId('asa_user_id_v2', 'user'));
    const tenantIdRef = useRef<string>(getOrCreateClientId('asa_tenant_id', 'tenant'));

    const updateMessages = useCallback((updater: (prev: Message[]) => Message[]) => {
        setMessages((prev) => {
            const next = updater(prev);
            messagesRef.current = next;
            return next;
        });
    }, []);

    const appendTraceLine = useCallback((assistantId: string, line: string) => {
        updateMessages((prev) =>
            prev.map((msg) => {
                if (msg.id !== assistantId) return msg;
                const existing = msg.traceLines || [];
                if (existing[existing.length - 1] === line) return msg;
                return { ...msg, traceLines: [...existing, line].slice(-80) };
            })
        );
    }, [updateMessages]);

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        setInput(e.target.value);
    };

    const runSingleQuestion = useCallback(async (question: string) => {
        const userMessage: Message = {
            id: Date.now().toString(),
            role: 'user',
            content: question,
        };

        const assistantMessageId = (Date.now() + 1).toString();

        const requestMessages = [...messagesRef.current, userMessage].map((msg) => ({
            role: msg.role,
            content: msg.content,
        }));

        updateMessages((prev) => [
            ...prev,
            userMessage,
            { id: assistantMessageId, role: 'assistant', content: '', traceLines: ['Started run'] },
        ]);

        setActiveAgent('planner');
        let accumulatedContent = '';

        try {
            const response = await fetch('/api/py/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    messages: requestMessages,
                    user_id: userIdRef.current,
                    tenant_id: tenantIdRef.current,
                    conversation_id: conversationIdRef.current,
                }),
            });

            if (!response.body) throw new Error('No response body');

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let lineBuffer = '';

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                lineBuffer += decoder.decode(value, { stream: true });
                const lines = lineBuffer.split('\n');
                lineBuffer = lines.pop() || '';

                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue;

                    try {
                        const data = JSON.parse(line.slice(6));

                        if (data.type === 'token') {
                            const tokenText = normalizeStreamContent(data.content);
                            if (!tokenText) continue;
                            accumulatedContent += tokenText;
                            updateMessages((prev) =>
                                prev.map((msg) =>
                                    msg.id === assistantMessageId
                                        ? { ...msg, content: accumulatedContent }
                                        : msg
                                )
                            );
                        } else if (data.type === 'agent_start') {
                            setActiveAgent(data.agent as AgentStatus);
                            appendTraceLine(assistantMessageId, `Agent started: ${String(data.agent)}`);
                        } else if (data.type === 'agent_end') {
                            appendTraceLine(assistantMessageId, `Agent completed: ${String(data.agent)}`);
                        } else if (data.type === 'tool_start') {
                            appendTraceLine(assistantMessageId, `Tool started: ${String(data.tool)}`);
                        } else if (data.type === 'tool_end') {
                            appendTraceLine(assistantMessageId, `Tool completed: ${String(data.tool)}`);
                        } else if (data.type === 'trace_run') {
                            appendTraceLine(assistantMessageId, `MLflow trace run: ${String(data.run_id)}`);
                        } else if (data.type === 'trace_link') {
                            appendTraceLine(assistantMessageId, `Trace UI: ${String(data.url)}`);
                        } else if (data.type === 'task_update') {
                            const taskId = String(data.task_id || 'task');
                            const status = formatTaskStatus(data.status);
                            appendTraceLine(assistantMessageId, `Task ${taskId}: ${status}`);
                        } else if (data.type === 'error') {
                            appendTraceLine(assistantMessageId, `Error: ${String(data.message)}`);
                        } else if (data.type === 'decision') {
                            if (data.reasoning) {
                                appendTraceLine(assistantMessageId, `Planner: ${String(data.reasoning)}`);
                            }
                            type DecisionStep = {
                                task_id?: string;
                                agent?: string;
                                depends_on?: string[];
                            };
                            const steps: DecisionStep[] = Array.isArray(data.steps) ? data.steps : [];
                            if (steps.length) {
                                const route = steps
                                    .map((step: DecisionStep) => {
                                        const taskId = String(step.task_id || '').trim();
                                        const agent = String(step.agent || '?');
                                        return taskId ? `${taskId}:${agent}` : agent;
                                    })
                                    .join(' -> ');
                                appendTraceLine(assistantMessageId, `Planned route: ${route}`);

                                const dependencyLines = steps
                                    .map((step: DecisionStep) => {
                                        const deps = Array.isArray(step.depends_on) ? step.depends_on : [];
                                        if (!deps.length) return '';
                                        const taskId = String(step.task_id || step.agent || '?');
                                        return `${taskId} depends on ${deps.join(', ')}`;
                                    })
                                    .filter(Boolean);
                                for (const depLine of dependencyLines.slice(0, 4)) {
                                    appendTraceLine(assistantMessageId, `Dependency: ${depLine}`);
                                }
                            }
                        } else if (data.type === 'final') {
                            const finalText = normalizeStreamContent(data.content);
                            if (finalText && finalText !== accumulatedContent) {
                                updateMessages((prev) =>
                                    prev.map((msg) =>
                                        msg.id === assistantMessageId
                                            ? { ...msg, content: finalText }
                                            : msg
                                    )
                                );
                            }
                        }
                    } catch (parseError) {
                        console.error('Error parsing SSE data', parseError);
                    }
                }
            }
        } catch (error) {
            console.error('Chat error:', error);
            updateMessages((prev) => [
                ...prev,
                { id: `err-${Date.now()}`, role: 'assistant', content: 'Sorry, I encountered an error.' },
            ]);
        }
    }, [appendTraceLine, updateMessages]);

    const sendMessage = useCallback(async (e?: React.FormEvent) => {
        if (e) e.preventDefault();
        if (!input.trim() || isLoading) return;
        const question = input.trim();

        setInput('');
        setIsLoading(true);

        try {
            await runSingleQuestion(question);
        } finally {
            setIsLoading(false);
            setActiveAgent('idle');
        }
    }, [input, isLoading, runSingleQuestion]);

    return {
        messages,
        input,
        handleInputChange,
        setInputValue: setInput,
        handleSubmit: sendMessage,
        isLoading,
        activeAgent,
        agentLabel: AGENT_LABELS[activeAgent]
    };
}
