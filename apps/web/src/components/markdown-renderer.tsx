import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { cn } from '@/lib/utils';

interface MarkdownRendererProps {
    content: string;
    className?: string;
}

export function MarkdownRenderer({ content, className }: MarkdownRendererProps) {
    return (
        <div className={cn('markdown-body text-sm leading-relaxed text-slate-800', className)}>
            <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                    // ── Headings ──────────────────────────────────────────────
                    h1({ children }) {
                        return (
                            <h1 className="mb-3 mt-6 text-xl font-bold tracking-tight text-slate-900 first:mt-0">
                                {children}
                            </h1>
                        );
                    },
                    h2({ children }) {
                        return (
                            <h2 className="mb-2 mt-5 text-base font-semibold text-slate-900 first:mt-0">
                                {children}
                            </h2>
                        );
                    },
                    h3({ children }) {
                        return (
                            <h3 className="mb-1.5 mt-4 text-sm font-semibold text-slate-800 first:mt-0">
                                {children}
                            </h3>
                        );
                    },
                    h4({ children }) {
                        return (
                            <h4 className="mb-1 mt-3 text-xs font-semibold uppercase tracking-wide text-slate-600 first:mt-0">
                                {children}
                            </h4>
                        );
                    },

                    // ── Paragraphs ────────────────────────────────────────────
                    p({ children }) {
                        return <p className="my-2 leading-relaxed text-slate-700">{children}</p>;
                    },

                    // ── Blockquote — used for Summary / Next step callouts ────
                    blockquote({ children }) {
                        return (
                            <blockquote className="my-3 rounded-r-lg border-l-4 border-[#1e66f5] bg-[#f0f5ff] px-4 py-2.5 text-sm text-slate-700">
                                {children}
                            </blockquote>
                        );
                    },

                    // ── Lists ─────────────────────────────────────────────────
                    ul({ children }) {
                        return <ul className="my-2 space-y-1 pl-5">{children}</ul>;
                    },
                    ol({ children }) {
                        return <ol className="my-2 list-decimal space-y-1 pl-5">{children}</ol>;
                    },
                    li({ children }) {
                        return (
                            <li className="relative text-slate-700 before:absolute before:-left-4 before:text-[#1e66f5] before:content-['•'] [ol_&]:before:content-none">
                                {children}
                            </li>
                        );
                    },

                    // ── Horizontal rule — section divider ─────────────────────
                    hr() {
                        return <hr className="my-5 border-slate-200" />;
                    },

                    // ── Inline code ───────────────────────────────────────────
                    code({ className: cls, children, ...props }) {
                        const match = /language-(\w+)/.exec(cls || '');
                        const isBlock = Boolean(match) || String(children).includes('\n');
                        if (isBlock) {
                            return (
                                <code
                                    className="my-3 block overflow-x-auto rounded-xl border border-slate-200 bg-slate-50 p-4 font-mono text-xs text-slate-800"
                                    {...props}
                                >
                                    {children}
                                </code>
                            );
                        }
                        return (
                            <code
                                className="rounded border border-slate-200 bg-slate-100 px-1.5 py-0.5 font-mono text-xs text-[#1e66f5]"
                                {...props}
                            >
                                {children}
                            </code>
                        );
                    },

                    // ── Tables ────────────────────────────────────────────────
                    table({ children }) {
                        return (
                            <div className="my-4 overflow-x-auto rounded-xl border border-slate-200 shadow-sm">
                                <table className="w-full border-collapse text-left text-sm">
                                    {children}
                                </table>
                            </div>
                        );
                    },
                    thead({ children }) {
                        return (
                            <thead className="bg-slate-50 text-xs font-semibold uppercase tracking-wide text-slate-500">
                                {children}
                            </thead>
                        );
                    },
                    tbody({ children }) {
                        return <tbody className="divide-y divide-slate-100">{children}</tbody>;
                    },
                    tr({ children }) {
                        return <tr className="hover:bg-slate-50 transition-colors">{children}</tr>;
                    },
                    th({ children }) {
                        return (
                            <th className="border-b border-slate-200 px-4 py-2.5 text-left">
                                {children}
                            </th>
                        );
                    },
                    td({ children }) {
                        return (
                            <td className="px-4 py-2.5 text-slate-700">{children}</td>
                        );
                    },

                    // ── Links ─────────────────────────────────────────────────
                    a({ children, href }) {
                        return (
                            <a
                                href={href}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="font-medium text-[#1e66f5] underline decoration-[#1e66f5]/30 underline-offset-2 hover:decoration-[#1e66f5]"
                            >
                                {children}
                            </a>
                        );
                    },

                    // ── Strong / Em ───────────────────────────────────────────
                    strong({ children }) {
                        return <strong className="font-semibold text-slate-900">{children}</strong>;
                    },
                    em({ children }) {
                        return <em className="italic text-slate-600">{children}</em>;
                    },
                }}
            >
                {content}
            </ReactMarkdown>
        </div>
    );
}
