'use client';

import { Search, Loader2 } from 'lucide-react';
import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { cn } from '@/lib/utils';

// Simplified mock search for now
// In real app, this would hit a ticker autocomplete API
const MOCK_SYMBOLS = [
    { symbol: 'AAPL', name: 'Apple Inc.' },
    { symbol: 'MSFT', name: 'Microsoft Corporation' },
    { symbol: 'GOOGL', name: 'Alphabet Inc.' },
    { symbol: 'AMZN', name: 'Amazon.com Inc.' },
    { symbol: 'NVDA', name: 'NVIDIA Corporation' },
    { symbol: 'TSLA', name: 'Tesla Inc.' },
    { symbol: 'META', name: 'Meta Platforms Inc.' },
    { symbol: 'BRK.B', name: 'Berkshire Hathaway Inc.' },
    { symbol: 'LLY', name: 'Eli Lilly and Company' },
    { symbol: 'AVGO', name: 'Broadcom Inc.' },
];

export function SymbolSearch({ className }: { className?: string }) {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<{ symbol: string; name: string }[]>([]);
    const [isOpen, setIsOpen] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const containerRef = useRef<HTMLDivElement>(null);
    const router = useRouter();

    useEffect(() => {
        if (query.length > 0) {
            setIsLoading(true);
            const timer = setTimeout(() => {
                const filtered = MOCK_SYMBOLS.filter(s =>
                    s.symbol.toLowerCase().includes(query.toLowerCase()) ||
                    s.name.toLowerCase().includes(query.toLowerCase())
                );
                setResults(filtered);
                setIsLoading(false);
                setIsOpen(true);
            }, 300);
            return () => clearTimeout(timer);
        } else {
            setResults([]);
            setIsOpen(false);
        }
    }, [query]);

    // Handle click outside
    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    const handleSelect = (symbol: string) => {
        router.push(`/research/${symbol}`);
        setIsOpen(false);
        setQuery('');
    };

    return (
        <div ref={containerRef} className={cn("relative", className)}>
            <div className="relative group">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-[#306ee8] transition-colors" size={16} />
                <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Search symbols..."
                    className="w-full bg-white/5 border border-white/10 rounded-xl py-2.5 pl-10 pr-4 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-[#306ee8]/50 focus:bg-white/[0.07] transition-all font-medium"
                />
                {isLoading && (
                    <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 text-[#306ee8] animate-spin" size={16} />
                )}
            </div>

            {isOpen && results.length > 0 && (
                <div className="absolute top-full left-0 right-0 mt-2 bg-[#1a1a1a] border border-white/10 rounded-xl shadow-2xl overflow-hidden z-[100] animate-in fade-in slide-in-from-top-2 duration-200">
                    <div className="max-h-64 overflow-y-auto p-1 custom-scrollbar">
                        {results.map((res) => (
                            <button
                                key={res.symbol}
                                onClick={() => handleSelect(res.symbol)}
                                className="w-full flex items-center justify-between p-3 hover:bg-white/5 rounded-lg transition-colors group"
                            >
                                <div className="flex flex-col items-start text-left">
                                    <span className="text-sm font-bold text-slate-200 group-hover:text-white">{res.symbol}</span>
                                    <span className="text-[10px] text-slate-500 font-bold uppercase tracking-tight truncate max-w-[150px]">{res.name}</span>
                                </div>
                                <div className="w-8 h-8 rounded bg-[#306ee8]/10 text-[#306ee8] flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                                    <Search size={14} />
                                </div>
                            </button>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
