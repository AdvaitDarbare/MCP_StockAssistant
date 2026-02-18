'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, Clock, ShieldAlert, ShieldCheck } from 'lucide-react';
import { MarkdownRenderer } from '@/components/markdown-renderer';
import type { ReportRunResponse } from '@/hooks/use-report-thread';

interface ReportResultCardProps {
    report: ReportRunResponse;
}

export function ReportResultCard({ report }: ReportResultCardProps) {
    const [showMeta, setShowMeta] = useState(false);

    const score = report.quality_gate?.score ?? null;
    const qualityLabel =
        score === null ? null
            : score >= 0.75 ? { text: `Quality ${Math.round(score * 100)}%`, color: 'text-emerald-600', Icon: ShieldCheck }
                : score >= 0.5 ? { text: `Quality ${Math.round(score * 100)}%`, color: 'text-amber-600', Icon: ShieldAlert }
                    : { text: `Quality ${Math.round(score * 100)}%`, color: 'text-rose-600', Icon: ShieldAlert };

    return (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
            {/* ── Pill bar ── */}
            <div className="flex flex-wrap items-center gap-2 border-b border-slate-100 bg-slate-50 px-4 py-2.5">
                <span className="rounded-full bg-[#e9f1ff] px-2.5 py-1 text-[11px] font-semibold text-[#1e66f5]">
                    {report.title}
                </span>
                {report.generation_ms != null && (
                    <span className="inline-flex items-center gap-1 text-[11px] text-slate-500">
                        <Clock size={11} />
                        {report.generation_ms} ms
                    </span>
                )}
                {qualityLabel && (
                    <span className={`inline-flex items-center gap-1 text-[11px] font-medium ${qualityLabel.color}`}>
                        <qualityLabel.Icon size={11} />
                        {qualityLabel.text}
                    </span>
                )}
            </div>

            {/* ── Report body — no fixed height, let it expand ── */}
            <div className="p-4">
                <MarkdownRenderer content={report.markdown || ''} />
            </div>

            {/* ── Collapsible metadata ── */}
            <div className="border-t border-slate-100">
                <button
                    onClick={() => setShowMeta(v => !v)}
                    className="flex w-full items-center justify-between px-4 py-2.5 text-[11px] font-medium text-slate-500 hover:bg-slate-50"
                >
                    <span>Sources &amp; tool plan</span>
                    {showMeta ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                </button>

                {showMeta && (
                    <div className="space-y-2 border-t border-slate-100 px-4 pb-4 pt-3 text-xs text-slate-600">
                        <div>
                            <span className="font-semibold text-slate-700">Sources: </span>
                            {(report.sources_used?.length ?? 0) > 0
                                ? report.sources_used!.join(', ')
                                : 'Not declared'}
                        </div>
                        <div>
                            <span className="font-semibold text-slate-700">Tools used: </span>
                            {(report.tool_plan?.length ?? 0) > 0
                                ? report.tool_plan!.map(t => t.tool).join(', ')
                                : 'Not declared'}
                        </div>
                        {(report.quality_gate?.warnings?.length ?? 0) > 0 && (
                            <div>
                                <span className="font-semibold text-amber-700">Warnings: </span>
                                {report.quality_gate!.warnings.join(', ')}
                            </div>
                        )}
                        {report.effective_prompt && (
                            <details className="mt-1">
                                <summary className="cursor-pointer font-semibold text-slate-700">
                                    Effective prompt
                                </summary>
                                <pre className="mt-1.5 whitespace-pre-wrap rounded-lg border border-slate-200 bg-slate-50 p-2.5 font-mono text-[10px] leading-relaxed text-slate-600">
                                    {report.effective_prompt}
                                </pre>
                            </details>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
