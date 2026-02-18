import { useCallback, useEffect, useMemo, useState } from 'react';

export interface ReportTemplate {
    id: string;
    title: string;
    default_prompt: string;
    effective_prompt: string;
    is_overridden: boolean;
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
            // If it starts with a prefix like 'user-', extract just the UUID part
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

export function useReportTemplates() {
    const [ownerKey, setOwnerKey] = useState<string>('');
    const [templates, setTemplates] = useState<ReportTemplate[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string>('');

    useEffect(() => {
        setOwnerKey(getOrCreateClientId('asa_user_id_v2', 'user'));
    }, []);

    const fetchTemplates = useCallback(async () => {
        if (!ownerKey) return;
        setIsLoading(true);
        setError('');
        try {
            const resp = await fetch(`/api/py/reports/templates?owner_key=${encodeURIComponent(ownerKey)}`);
            const json = await resp.json();
            if (!resp.ok) throw new Error(json.detail || 'Failed to load templates');
            setTemplates(Array.isArray(json.templates) ? json.templates : []);
        } catch (e) {
            setError(e instanceof Error ? e.message : 'Failed to load templates');
        } finally {
            setIsLoading(false);
        }
    }, [ownerKey]);

    useEffect(() => {
        fetchTemplates();
    }, [fetchTemplates]);

    const saveTemplate = useCallback(
        async (reportType: string, promptText: string) => {
            if (!ownerKey) throw new Error('Missing owner key');
            const resp = await fetch(`/api/py/reports/templates/${reportType}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ owner_key: ownerKey, prompt_text: promptText }),
            });
            const json = await resp.json();
            if (!resp.ok) throw new Error(json.detail || 'Failed to save template');
            await fetchTemplates();
            return json;
        },
        [ownerKey, fetchTemplates]
    );

    const resetTemplate = useCallback(
        async (reportType: string) => {
            if (!ownerKey) throw new Error('Missing owner key');
            const resp = await fetch(
                `/api/py/reports/templates/${reportType}?owner_key=${encodeURIComponent(ownerKey)}`,
                { method: 'DELETE' }
            );
            const json = await resp.json();
            if (!resp.ok) throw new Error(json.detail || 'Failed to reset template');
            await fetchTemplates();
            return json;
        },
        [ownerKey, fetchTemplates]
    );

    const templateMap = useMemo(() => {
        const map = new Map<string, ReportTemplate>();
        for (const template of templates) map.set(template.id, template);
        return map;
    }, [templates]);

    return {
        ownerKey,
        templates,
        templateMap,
        isLoading,
        error,
        refreshTemplates: fetchTemplates,
        saveTemplate,
        resetTemplate,
    };
}
