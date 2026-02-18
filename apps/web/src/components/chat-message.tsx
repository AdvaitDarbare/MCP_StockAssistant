import { cn } from "@/lib/utils";
import { User, Sparkles } from "lucide-react";
import { MarkdownRenderer } from "./markdown-renderer";
import { StockChart } from "./stock-chart";
import { Skeleton } from "./ui/skeleton";

interface ChatMessageProps {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    message: any;
}

export function ChatMessage({ message }: ChatMessageProps) {
    const isUser = message.role === "user";

    return (
        <div className="flex gap-3">
            <div
                className={cn(
                    "mt-1 grid h-8 w-8 flex-shrink-0 place-items-center rounded-full border",
                    isUser
                        ? "border-slate-300 bg-slate-100 text-slate-700"
                        : "border-[#bcd2ff] bg-[#e9f1ff] text-[#1e66f5]"
                )}
            >
                {isUser ? <User size={14} /> : <Sparkles size={14} />}
            </div>

            <div
                className={cn(
                    "min-w-0 flex-1 rounded-2xl border px-4 py-3",
                    isUser ? "border-slate-200 bg-slate-50" : "border-slate-200 bg-white"
                )}
            >
                <div className={cn("mb-2 text-xs font-semibold", isUser ? "text-slate-500" : "text-[#1e66f5]")}>{isUser ? "You" : "Assistant"}</div>

                {!isUser && Array.isArray(message.traceLines) && message.traceLines.length > 0 ? (
                    <details className="mb-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
                        <summary className="cursor-pointer text-[11px] font-semibold uppercase tracking-wider text-slate-500 hover:text-slate-700">
                            Debug Info ({message.traceLines.length} events)
                        </summary>
                        <div className="mt-2 max-h-32 space-y-1 overflow-y-auto pr-1 font-mono text-xs text-slate-500">
                            {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                            {message.traceLines
                                .filter((line: any) => {
                                    const lineStr = String(line);
                                    // Hide verbose trace lines for cleaner UX
                                    return !lineStr.includes('MLflow trace run') && 
                                           !lineStr.includes('Trace UI') &&
                                           !lineStr.includes('Tool started:') &&
                                           !lineStr.includes('Tool completed:') &&
                                           !lineStr.includes('Agent started:') &&
                                           !lineStr.includes('Agent completed:');
                                })
                                .slice(-10) // Only show last 10 relevant events
                                .map((line: any, idx: number) => (
                                <div key={`${idx}-${line}`} className="break-words">
                                    {String(line)}
                                </div>
                            ))}
                        </div>
                    </details>
                ) : null}

                {message.content ? <MarkdownRenderer content={message.content} /> : null}

                <div className="mt-4 space-y-4">
                    {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                    {message.toolInvocations?.map((toolInvocation: any) => {
                        const { toolName, toolCallId, state } = toolInvocation;

                        if (state === 'result' && toolName === 'get_historical_prices') {
                            const { result } = toolInvocation;
                            return (
                                <div key={toolCallId} className="w-full overflow-hidden rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                                    <div className="mb-4 flex items-center justify-between">
                                        <div>
                                            <h4 className="text-sm font-semibold text-slate-900">{toolInvocation.args.symbol} Price History</h4>
                                            <p className="text-xs text-slate-500">Recent trend view</p>
                                        </div>
                                        <span className="rounded-full bg-[#e9f1ff] px-2 py-1 text-[10px] font-semibold uppercase text-[#1e66f5]">
                                            Live
                                        </span>
                                    </div>
                                    <div className="relative h-[260px] w-full">
                                        <StockChart data={result.prices || result} />
                                    </div>
                                </div>
                            );
                        }

                        return (
                            <div key={toolCallId} className="w-full rounded-xl border border-slate-200 bg-slate-50 p-4">
                                <div className="mb-3 flex items-center gap-2 text-sm text-slate-500">
                                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-[#1e66f5] border-t-transparent" />
                                    <span>Analyzing {toolName}...</span>
                                </div>
                                <Skeleton className="h-[120px] w-full rounded-lg bg-white" />
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
}
