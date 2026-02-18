'use client';

import { useRef, useState } from 'react';
import { ArrowUp, RefreshCw, RotateCcw } from 'lucide-react';
import { MarkdownRenderer } from '@/components/markdown-renderer';
import type { ReportThreadMessage } from '@/hooks/use-report-thread';

interface ReportThreadProps {
    messages: ReportThreadMessage[];
    canFollowUp: boolean;
    isFollowingUp: boolean;
    threadId: string;
    onFollowUp: (question: string, refreshData: boolean) => Promise<void>;
    onReset: () => void;
}

export function ReportThread({ messages, canFollowUp, isFollowingUp, threadId, onFollowUp, onReset }: ReportThreadProps) {
    const [question, setQuestion] = useState('');
    const [refreshData, setRefreshData] = useState(false);
    const [error, setError] = useState('');
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        const q = question.trim();
        if (!q || isFollowingUp) return;
        setError('');
        try {
            await onFollowUp(q, refreshData);
            setQuestion('');
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Follow-up failed');
        }
    }

    function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit(e as unknown as React.FormEvent);
        }
    }

    if (messages.length === 0) return null;

    return (
        <div className="flex flex-col gap-3">
            {/* Thread header */}
            <div className="flex items-center justify-between">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Thread
                    {threadId ? (
                        <span className="ml-1.5 font-mono text-[10px] text-slate-400">
                            #{threadId.slice(0, 8)}
                        </span>
                    ) : null}
                </p>
                <button
                    onClick={onReset}
                    className="inline-flex items-center gap-1 rounded border border-slate-200 bg-white px-2 py-1 text-[11px] text-slate-500 hover:bg-slate-50"
                >
                    <RotateCcw size={10} />
                    New thread
                </button>
            </div>

            {/* Messages */}
            <div className="space-y-3">
                {messages.map((msg) => (
                    <div key={msg.id} className={msg.role === 'user' ? 'flex justify-end' : 'flex justify-start'}>
                        {msg.role === 'user' ? (
                            <div className="max-w-[85%] rounded-xl rounded-tr-sm bg-[#1e66f5] px-3 py-2 text-xs text-white">
                                {msg.content}
                            </div>
                        ) : (
                            <div className="w-full rounded-xl rounded-tl-sm border border-slate-200 bg-slate-50 p-3">
                                <MarkdownRenderer
                                    content={msg.content}
                                    className="prose-sm prose-p:my-1.5 prose-headings:text-sm"
                                />
                            </div>
                        )}
                    </div>
                ))}

                {isFollowingUp && (
                    <div className="flex items-center gap-2 text-xs text-slate-500">
                        <RefreshCw size={12} className="animate-spin text-[#1e66f5]" />
                        Generating follow-up…
                    </div>
                )}
            </div>

            {/* Follow-up input */}
            {canFollowUp && (
                <form onSubmit={handleSubmit} className="mt-1 space-y-2">
                    {error && <p className="text-[11px] text-rose-600">{error}</p>}
                    <div className="flex items-end gap-2">
                        <textarea
                            ref={textareaRef}
                            rows={2}
                            value={question}
                            onChange={(e) => setQuestion(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder="Ask a follow-up (Enter to send, Shift+Enter for newline)"
                            disabled={isFollowingUp}
                            className="min-h-[44px] flex-1 resize-none rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#1e66f5]/30 disabled:opacity-50"
                        />
                        <button
                            type="submit"
                            disabled={isFollowingUp || !question.trim()}
                            className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#1e66f5] text-white hover:bg-[#1655d5] disabled:opacity-50"
                        >
                            {isFollowingUp ? (
                                <RefreshCw size={13} className="animate-spin" />
                            ) : (
                                <ArrowUp size={13} />
                            )}
                        </button>
                    </div>
                    <label className="flex cursor-pointer items-center gap-2 text-[11px] text-slate-500">
                        <input
                            type="checkbox"
                            checked={refreshData}
                            onChange={(e) => setRefreshData(e.target.checked)}
                            className="h-3 w-3 rounded border-slate-300 accent-[#1e66f5]"
                        />
                        Refresh market data before answering
                    </label>
                </form>
            )}
        </div>
    );
}
