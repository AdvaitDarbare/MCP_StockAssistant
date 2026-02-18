'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, ExternalLink, RefreshCw, ShieldCheck } from 'lucide-react';

import { Button } from '@/components/ui/button';

type SchwabStatus = {
    configured: boolean;
    token_exists: boolean;
    client_ready: boolean;
    redirect_uri: string;
    token_path: string;
    client_id_suffix?: string;
    last_error?: string | null;
};

export default function SchwabIntegrationPage() {
    const [status, setStatus] = useState<{ market: SchwabStatus; trader: SchwabStatus } | null>(null);
    const [selectedApp, setSelectedApp] = useState<'market' | 'trader'>('market');
    const [authorizeUrl, setAuthorizeUrl] = useState<string>('');
    const [code, setCode] = useState('');
    const [exchangeMessage, setExchangeMessage] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const refreshStatus = useCallback(async (app: 'market' | 'trader' = selectedApp) => {
        const [statusResp, authResp] = await Promise.all([
            fetch('/api/py/schwab/status'),
            fetch(`/api/py/schwab/oauth/authorize-url?app=${app}`),
        ]);
        const statusJson = await statusResp.json();
        const authJson = await authResp.json();
        setStatus({ market: statusJson.market, trader: statusJson.trader });
        setAuthorizeUrl(authJson.authorize_url || '');
    }, [selectedApp]);

    useEffect(() => {
        refreshStatus().catch(() => {
            setExchangeMessage('Failed to load Schwab integration status.');
        });
    }, [refreshStatus]);

    async function exchangeCode() {
        setIsLoading(true);
        setExchangeMessage('');
        try {
            const resp = await fetch('/api/py/schwab/oauth/exchange', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code, app: selectedApp }),
            });
            const json = await resp.json();
            if (!resp.ok) {
                throw new Error(typeof json.detail === 'string' ? json.detail : JSON.stringify(json.detail));
            }
            setExchangeMessage(`Token saved for ${selectedApp}. Expires in: ${json.expires_in ?? 'unknown'} seconds.`);
            await refreshStatus();
        } catch (e) {
            setExchangeMessage(e instanceof Error ? e.message : 'Token exchange failed.');
        } finally {
            setIsLoading(false);
        }
    }

    async function refreshToken() {
        setIsLoading(true);
        setExchangeMessage('');
        try {
            const resp = await fetch('/api/py/schwab/oauth/refresh', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ app: selectedApp }),
            });
            const json = await resp.json();
            if (!resp.ok) {
                throw new Error(typeof json.detail === 'string' ? json.detail : JSON.stringify(json.detail));
            }
            setExchangeMessage(`Token refreshed for ${selectedApp}. Expires in: ${json.expires_in ?? 'unknown'} seconds.`);
            await refreshStatus();
        } catch (e) {
            setExchangeMessage(e instanceof Error ? e.message : 'Token refresh failed.');
        } finally {
            setIsLoading(false);
        }
    }

    return (
        <div className="min-h-screen overflow-y-auto bg-[radial-gradient(circle_at_0%_0%,#eaf1ff_0%,#f4f7fb_45%,#f9fbff_100%)] text-slate-900">
            <div className="mx-auto max-w-4xl px-4 py-5 sm:px-6">
                <header className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200/80 bg-white/85 px-4 py-3 shadow-[0_12px_32px_rgba(15,23,42,0.06)] backdrop-blur">
                    <div className="flex items-center gap-3">
                        <Link
                            href="/"
                            className="grid h-9 w-9 place-items-center rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                        >
                            <ArrowLeft size={16} />
                        </Link>
                        <div>
                            <h1 className="text-base font-semibold tracking-tight">Schwab Integration</h1>
                            <p className="text-xs text-slate-500">Connect market/trader apps and manage OAuth tokens.</p>
                        </div>
                    </div>
                    <Button
                        variant="outline"
                        className="h-9 border-slate-300 bg-white text-slate-700 hover:bg-slate-50"
                        onClick={() => refreshStatus()}
                    >
                        <RefreshCw size={14} className="mr-2" />
                        Refresh
                    </Button>
                </header>

                <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
                    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-[0_16px_40px_rgba(15,23,42,0.08)]">
                        <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Connection status</h2>
                        {!status ? (
                            <div className="mt-3 text-sm text-slate-500">Loading status...</div>
                        ) : (
                            <div className="mt-3 space-y-3">
                                {(['market', 'trader'] as const).map((app) => (
                                    <div key={app} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                                        <div className="mb-2 flex items-center justify-between">
                                            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">{app} app</span>
                                            <span className="text-xs text-slate-500">Client suffix: {status[app].client_id_suffix || 'n/a'}</span>
                                        </div>
                                        <div className="grid grid-cols-1 gap-1 text-sm text-slate-700 sm:grid-cols-2">
                                            <div>Configured: <strong>{String(status[app].configured)}</strong></div>
                                            <div>Token exists: <strong>{String(status[app].token_exists)}</strong></div>
                                            <div>Client ready: <strong>{String(status[app].client_ready)}</strong></div>
                                            <div className="truncate">Token path: <strong>{status[app].token_path}</strong></div>
                                        </div>
                                        {status[app].last_error ? (
                                            <div className="mt-2 text-xs text-rose-700">Last error: {status[app].last_error}</div>
                                        ) : null}
                                    </div>
                                ))}
                            </div>
                        )}
                    </section>

                    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-[0_16px_40px_rgba(15,23,42,0.08)]">
                        <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">OAuth setup</h2>

                        <div className="mt-3 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-800">
                            <span className="inline-flex items-center gap-1 font-medium"><ShieldCheck size={13} /> Trade submission remains HITL-gated.</span>
                        </div>

                        <div className="mt-3 space-y-3">
                            <div>
                                <label className="mb-1 block text-xs text-slate-500">App</label>
                                <select
                                    value={selectedApp}
                                    onChange={(e) => setSelectedApp(e.target.value as 'market' | 'trader')}
                                    className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm"
                                >
                                    <option value="market">Market Data App</option>
                                    <option value="trader">Accounts & Trading App</option>
                                </select>
                            </div>

                            <div>
                                <label className="mb-1 block text-xs text-slate-500">Authorize URL</label>
                                <div className="flex gap-2">
                                    <input
                                        value={authorizeUrl}
                                        readOnly
                                        className="h-10 flex-1 rounded-lg border border-slate-300 bg-slate-50 px-3 text-xs text-slate-700"
                                    />
                                    <a
                                        href={authorizeUrl || '#'}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="inline-flex h-10 items-center rounded-lg bg-[#1e66f5] px-4 text-xs font-semibold text-white hover:bg-[#1655d5]"
                                    >
                                        Open <ExternalLink size={13} className="ml-1.5" />
                                    </a>
                                </div>
                            </div>

                            <div>
                                <label className="mb-1 block text-xs text-slate-500">Authorization code</label>
                                <input
                                    value={code}
                                    onChange={(e) => setCode(e.target.value)}
                                    placeholder="Paste code from redirect URL"
                                    className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm"
                                />
                            </div>

                            <div className="flex gap-2">
                                <Button onClick={exchangeCode} disabled={!code || isLoading} className="bg-[#1e66f5] text-white hover:bg-[#1655d5]">
                                    Exchange code
                                </Button>
                                <Button
                                    onClick={refreshToken}
                                    disabled={isLoading}
                                    variant="outline"
                                    className="border-slate-300 bg-white text-slate-700 hover:bg-slate-50"
                                >
                                    Refresh token
                                </Button>
                            </div>

                            {exchangeMessage ? (
                                <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-700">
                                    {exchangeMessage}
                                </div>
                            ) : null}
                        </div>
                    </section>
                </div>
            </div>
        </div>
    );
}
