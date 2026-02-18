'use client';

import { useState } from 'react';
import { Check, ChevronDown, ChevronUp, RefreshCw, RotateCcw } from 'lucide-react';
import type { ReportTemplate } from '@/hooks/use-report-templates';

interface TemplateEditorProps {
    template: ReportTemplate;
    onSave: (reportType: string, promptText: string) => Promise<void>;
    onReset: (reportType: string) => Promise<void>;
}

export function TemplateEditor({ template, onSave, onReset }: TemplateEditorProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [editText, setEditText] = useState(template.effective_prompt);
    const [isSaving, setIsSaving] = useState(false);
    const [isResetting, setIsResetting] = useState(false);
    const [saved, setSaved] = useState(false);
    const [error, setError] = useState('');

    const isDirty = editText !== template.effective_prompt;

    async function handleSave() {
        if (!editText.trim()) { setError('Prompt cannot be empty.'); return; }
        setIsSaving(true); setError('');
        try {
            await onSave(template.id, editText.trim());
            setSaved(true);
            setTimeout(() => setSaved(false), 2000);
        } catch (e) {
            setError(e instanceof Error ? e.message : 'Save failed');
        } finally {
            setIsSaving(false);
        }
    }

    async function handleReset() {
        setIsResetting(true); setError('');
        try {
            await onReset(template.id);
            setEditText(template.default_prompt);
        } catch (e) {
            setError(e instanceof Error ? e.message : 'Reset failed');
        } finally {
            setIsResetting(false);
        }
    }

    return (
        <div className={`rounded-xl border transition-colors ${isOpen ? 'border-[#1e66f5]/30 bg-[#f5f8ff]' : 'border-slate-200 bg-white'}`}>
            {/* Header row — always visible */}
            <button
                onClick={() => setIsOpen(v => !v)}
                className="flex w-full items-center justify-between px-4 py-3 text-left"
            >
                <div className="flex items-center gap-2 min-w-0">
                    <span className="truncate text-sm font-medium text-slate-800">{template.title}</span>
                    {template.is_overridden && (
                        <span className="shrink-0 rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-700">
                            Edited
                        </span>
                    )}
                </div>
                {isOpen ? <ChevronUp size={15} className="shrink-0 text-slate-400" /> : <ChevronDown size={15} className="shrink-0 text-slate-400" />}
            </button>

            {/* Expanded body */}
            {isOpen && (
                <div className="border-t border-slate-200 px-4 pb-4 pt-3 space-y-3">
                    <textarea
                        value={editText}
                        onChange={e => { setEditText(e.target.value); setError(''); }}
                        rows={10}
                        className="w-full resize-y rounded-lg border border-slate-300 bg-white px-3 py-2.5 font-mono text-xs leading-relaxed text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#1e66f5]/30"
                        spellCheck={false}
                    />
                    {error && <p className="text-xs text-rose-600">{error}</p>}
                    <div className="flex items-center gap-2">
                        <button
                            onClick={handleSave}
                            disabled={isSaving || !isDirty}
                            className="inline-flex items-center gap-1.5 rounded-lg bg-[#1e66f5] px-3 py-1.5 text-xs font-semibold text-white hover:bg-[#1655d5] disabled:opacity-50"
                        >
                            {isSaving
                                ? <RefreshCw size={11} className="animate-spin" />
                                : saved
                                    ? <Check size={11} />
                                    : <Check size={11} />}
                            {saved ? 'Saved!' : 'Save changes'}
                        </button>
                        {template.is_overridden && (
                            <button
                                onClick={handleReset}
                                disabled={isResetting}
                                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-50 disabled:opacity-50"
                            >
                                {isResetting
                                    ? <RefreshCw size={11} className="animate-spin" />
                                    : <RotateCcw size={11} />}
                                Reset to default
                            </button>
                        )}
                        {isDirty && !isSaving && (
                            <span className="text-[11px] text-amber-600">Unsaved changes</span>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
