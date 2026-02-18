'use client';

import { useState } from 'react';
import {
    AlertCircle,
    ChevronDown,
    ChevronUp,
    FlaskConical,
    Loader2,
    Play,
    Settings2,
    X,
} from 'lucide-react';
import { useReportTemplates } from '@/hooks/use-report-templates';
import { useReportThread } from '@/hooks/use-report-thread';
import { TemplateEditor } from './template-editor';
import { ReportResultCard } from './report-result-card';
import { ReportThread } from './report-thread';

// Sensible default payloads per workflow
const EXAMPLE_PAYLOADS: Record<string, Record<string, unknown>> = {
    goldman_screener: { limit: 10 },
    morgan_dcf: { ticker: 'AAPL', company: 'Apple Inc' },
    bridgewater_risk: { holdings: [{ symbol: 'AAPL', weight: 0.25 }, { symbol: 'MSFT', weight: 0.2 }, { symbol: 'NVDA', weight: 0.2 }, { symbol: 'JPM', weight: 0.15 }, { symbol: 'XOM', weight: 0.2 }] },
    jpm_earnings: { ticker: 'NVDA', company: 'NVIDIA' },
    blackrock_builder: { details: { age: 34, income: 190000, savings: 400000, goals: ['long-term growth'], risk_tolerance: 'moderate', account_type: 'taxable', monthly_investment: 3000 } },
    citadel_technical: { /* ticker extracted from prompt */ },
    harvard_dividend: { investment_amount: 500000, monthly_income_goal: 1800, account_type: 'taxable', tax_bracket: '24%' },
    bain_competitive: { sector: 'semiconductors' },
    renaissance_pattern: { ticker: 'AMD', years: 5 },
    mckinsey_macro: { holdings: [{ symbol: 'AAPL', weight: 0.2 }, { symbol: 'MSFT', weight: 0.2 }, { symbol: 'QQQ', weight: 0.3 }, { symbol: 'BND', weight: 0.3 }], biggest_concern: 'rates staying high' },
};

// Which workflows need a ticker/sector input
const NEEDS_TICKER = ['morgan_dcf', 'jpm_earnings', 'citadel_technical', 'renaissance_pattern'];
const NEEDS_SECTOR = ['bain_competitive'];

interface ReportLabPanelProps {
    onClose: () => void;
}

export function ReportLabPanel({ onClose }: ReportLabPanelProps) {
    const {
        ownerKey,
        templates,
        isLoading: templatesLoading,
        error: templatesError,
        saveTemplate,
        resetTemplate,
    } = useReportTemplates();

    const {
        currentReport,
        threadId,
        messages,
        isRunning,
        isFollowingUp,
        error: threadError,
        canFollowUp,
        runReport,
        followUp,
        resetThread,
    } = useReportThread();

    const [selectedType, setSelectedType] = useState('goldman_screener');
    const [ticker, setTicker] = useState('');
    const [activeTab, setActiveTab] = useState<'run' | 'templates'>('run');
    const [showPromptPreview, setShowPromptPreview] = useState(false);

    const selectedTemplate = templates.find(t => t.id === selectedType);
    const needsTicker = NEEDS_TICKER.includes(selectedType);
    const needsSector = NEEDS_SECTOR.includes(selectedType);
    const showTickerInput = needsTicker || needsSector;

    function buildPayload(): Record<string, unknown> {
        const base = { ...(EXAMPLE_PAYLOADS[selectedType] ?? {}) };
        if (ticker.trim()) {
            if (needsTicker) base.ticker = ticker.trim().toUpperCase();
            if (needsSector) base.sector = ticker.trim().toLowerCase();
        }
        return base;
    }

    async function handleRun() {
        if (!ownerKey) return;
        resetThread();
        await runReport({ reportType: selectedType, payload: buildPayload(), ownerKey });
    }

    async function handleFollowUp(question: string, refreshData: boolean) {
        if (!ownerKey || !threadId) return;
        await followUp({ reportType: selectedType, ownerKey, threadId, question, refreshData });
    }

    const error = threadError || templatesError;
    const isBackendDown = error?.toLowerCase().includes('method not allowed') ||
        error?.toLowerCase().includes('failed to fetch') ||
        error?.toLowerCase().includes('networkerror');

    return (
        <div className="flex h-full flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-[0_16px_40px_rgba(15,23,42,0.10)]">

            {/* ── Header ── */}
            <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
                <div className="flex items-center gap-2">
                    <div className="grid h-7 w-7 place-items-center rounded-lg bg-[#e9f1ff] text-[#1e66f5]">
                        <FlaskConical size={14} />
                    </div>
                    <div>
                        <p className="text-sm font-semibold text-slate-900">Report Lab</p>
                        <p className="text-[10px] text-slate-500">Institutional research workflows</p>
                    </div>
                </div>
                <button
                    onClick={onClose}
                    className="grid h-7 w-7 place-items-center rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-50"
                    aria-label="Close"
                >
                    <X size={14} />
                </button>
            </div>

            {/* ── Tab bar ── */}
            <div className="flex border-b border-slate-100">
                <button
                    onClick={() => setActiveTab('run')}
                    className={`flex-1 py-2.5 text-xs font-semibold transition-colors ${activeTab === 'run' ? 'border-b-2 border-[#1e66f5] text-[#1e66f5]' : 'text-slate-500 hover:text-slate-700'}`}
                >
                    Run Report
                </button>
                <button
                    onClick={() => setActiveTab('templates')}
                    className={`flex-1 py-2.5 text-xs font-semibold transition-colors ${activeTab === 'templates' ? 'border-b-2 border-[#1e66f5] text-[#1e66f5]' : 'text-slate-500 hover:text-slate-700'}`}
                >
                    <Settings2 size={11} className="mr-1 inline" />
                    Edit Prompts
                </button>
            </div>

            {/* ── Scrollable body ── */}
            <div className="flex-1 overflow-y-auto">

                {/* ════════════ RUN TAB ════════════ */}
                {activeTab === 'run' && (
                    <div className="space-y-4 p-4">

                        {/* Backend-down banner */}
                        {isBackendDown && (
                            <div className="flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
                                <AlertCircle size={14} className="mt-0.5 shrink-0" />
                                <div>
                                    <p className="font-semibold">API server not reachable</p>
                                    <p className="mt-0.5 text-amber-700">Make sure the FastAPI backend is running on port 8001.</p>
                                    <code className="mt-1 block rounded bg-amber-100 px-2 py-1 font-mono text-[10px]">
                                        cd apps/api && uvicorn gateway.main:app --port 8001 --reload
                                    </code>
                                </div>
                            </div>
                        )}

                        {/* Workflow selector */}
                        <div className="space-y-1.5">
                            <label className="block text-xs font-semibold text-slate-600">Workflow</label>
                            <select
                                value={selectedType}
                                onChange={e => { setSelectedType(e.target.value); resetThread(); setTicker(''); }}
                                className="h-9 w-full rounded-lg border border-slate-300 bg-white px-3 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#1e66f5]/30"
                            >
                                {templates.length > 0
                                    ? templates.map(t => (
                                        <option key={t.id} value={t.id}>
                                            {t.title}{t.is_overridden ? ' ✎' : ''}
                                        </option>
                                    ))
                                    : (
                                        // Fallback while templates load
                                        <>
                                            <option value="goldman_screener">Goldman Sachs Stock Screener</option>
                                            <option value="morgan_dcf">Morgan Stanley DCF Valuation</option>
                                            <option value="bridgewater_risk">Bridgewater Risk Parity</option>
                                            <option value="jpm_earnings">JPMorgan Earnings Brief</option>
                                            <option value="blackrock_builder">BlackRock Portfolio Builder</option>
                                            <option value="citadel_technical">Citadel Technical Analysis</option>
                                            <option value="harvard_dividend">Harvard Dividend Income</option>
                                            <option value="bain_competitive">Bain Competitive Intelligence</option>
                                            <option value="renaissance_pattern">Renaissance Pattern Recognition</option>
                                            <option value="mckinsey_macro">McKinsey Macro Overlay</option>
                                        </>
                                    )
                                }
                            </select>
                        </div>

                        {/* Ticker / sector input */}
                        {showTickerInput && (
                            <div className="space-y-1.5">
                                <label className="block text-xs font-semibold text-slate-600">
                                    {needsSector ? 'Sector' : 'Ticker symbol'}
                                </label>
                                <input
                                    value={ticker}
                                    onChange={e => setTicker(e.target.value)}
                                    placeholder={needsSector ? 'e.g. semiconductors' : 'e.g. AAPL'}
                                    className="h-9 w-full rounded-lg border border-slate-300 bg-white px-3 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#1e66f5]/30"
                                />
                            </div>
                        )}

                        {/* Active prompt preview (collapsible) */}
                        {selectedTemplate && (
                            <div className="rounded-lg border border-slate-200 bg-slate-50">
                                <button
                                    onClick={() => setShowPromptPreview(v => !v)}
                                    className="flex w-full items-center justify-between px-3 py-2 text-xs"
                                >
                                    <span className="font-medium text-slate-600">
                                        Active prompt
                                        {selectedTemplate.is_overridden && (
                                            <span className="ml-1.5 rounded-full bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold text-amber-700">
                                                Custom
                                            </span>
                                        )}
                                    </span>
                                    {showPromptPreview
                                        ? <ChevronUp size={12} className="text-slate-400" />
                                        : <ChevronDown size={12} className="text-slate-400" />}
                                </button>
                                {showPromptPreview && (
                                    <pre className="border-t border-slate-200 px-3 pb-3 pt-2 font-mono text-[10px] leading-relaxed text-slate-600 whitespace-pre-wrap max-h-[160px] overflow-y-auto">
                                        {selectedTemplate.effective_prompt}
                                    </pre>
                                )}
                            </div>
                        )}

                        {/* Run button */}
                        <button
                            onClick={handleRun}
                            disabled={isRunning || !ownerKey}
                            className="flex h-10 w-full items-center justify-center gap-2 rounded-lg bg-[#1e66f5] text-sm font-semibold text-white hover:bg-[#1655d5] disabled:opacity-60 transition-colors"
                        >
                            {isRunning
                                ? <><Loader2 size={14} className="animate-spin" /> Generating…</>
                                : <><Play size={14} /> {currentReport ? 'Run again' : 'Run report'}</>
                            }
                        </button>

                        {/* Non-backend errors */}
                        {error && !isBackendDown && (
                            <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">
                                {error}
                            </div>
                        )}

                        {/* Result */}
                        {currentReport && messages.length === 0 && (
                            <ReportResultCard report={currentReport} />
                        )}

                        {/* Thread */}
                        {messages.length > 0 && (
                            <ReportThread
                                messages={messages}
                                canFollowUp={canFollowUp}
                                isFollowingUp={isFollowingUp}
                                threadId={threadId}
                                onFollowUp={handleFollowUp}
                                onReset={resetThread}
                            />
                        )}

                        {/* Empty state */}
                        {!currentReport && !isRunning && !error && (
                            <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 p-6 text-center">
                                <FlaskConical size={22} className="mx-auto mb-2 text-slate-300" />
                                <p className="text-xs font-medium text-slate-600">No report yet</p>
                                <p className="mt-1 text-[11px] text-slate-400">
                                    Pick a workflow above and hit <strong>Run report</strong>.
                                </p>
                            </div>
                        )}
                    </div>
                )}

                {/* ════════════ TEMPLATES TAB ════════════ */}
                {activeTab === 'templates' && (
                    <div className="p-4 space-y-3">
                        <p className="text-xs text-slate-500 leading-relaxed">
                            Each workflow has a built-in prompt. Click any card to expand and edit it.
                            Changes are saved to your account and override the defaults.
                        </p>

                        {templatesLoading && (
                            <div className="flex items-center gap-2 py-4 text-xs text-slate-500">
                                <Loader2 size={13} className="animate-spin text-[#1e66f5]" />
                                Loading prompts…
                            </div>
                        )}

                        {!templatesLoading && templates.length === 0 && (
                            <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 p-5 text-center">
                                <AlertCircle size={18} className="mx-auto mb-2 text-slate-400" />
                                <p className="text-xs font-medium text-slate-600">Could not load templates</p>
                                <p className="mt-1 text-[11px] text-slate-400">
                                    Make sure the API backend is running on port 8001.
                                </p>
                            </div>
                        )}

                        {templates.map(template => (
                            <TemplateEditor
                                key={template.id}
                                template={template}
                                onSave={saveTemplate}
                                onReset={resetTemplate}
                            />
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
