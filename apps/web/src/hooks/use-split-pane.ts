import { useCallback, useEffect, useMemo, useState } from 'react';

const PANEL_OPEN_KEY = 'asa_report_lab_open';
const PANEL_WIDTH_KEY = 'asa_report_lab_width';

const DEFAULT_WIDTH = 440;
const MIN_WIDTH = 360;
const MAX_WIDTH = 760;

function clampWidth(width: number) {
    return Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, width));
}

export function useSplitPane() {
    const [isOpen, setIsOpen] = useState(false);
    const [panelWidth, setPanelWidth] = useState(DEFAULT_WIDTH);
    const [isResizing, setIsResizing] = useState(false);

    useEffect(() => {
        if (typeof window === 'undefined') return;
        try {
            const savedOpen = window.localStorage.getItem(PANEL_OPEN_KEY);
            const savedWidth = window.localStorage.getItem(PANEL_WIDTH_KEY);
            if (savedOpen != null) setIsOpen(savedOpen === 'true');
            if (savedWidth != null) {
                const parsed = Number(savedWidth);
                if (Number.isFinite(parsed)) setPanelWidth(clampWidth(parsed));
            }
        } catch {
            // ignore storage failures
        }
    }, []);

    const persist = useCallback((open: boolean, width: number) => {
        if (typeof window === 'undefined') return;
        try {
            window.localStorage.setItem(PANEL_OPEN_KEY, String(open));
            window.localStorage.setItem(PANEL_WIDTH_KEY, String(clampWidth(width)));
        } catch {
            // ignore storage failures
        }
    }, []);

    const open = useCallback(() => {
        setIsOpen(true);
        persist(true, panelWidth);
    }, [panelWidth, persist]);

    const close = useCallback(() => {
        setIsOpen(false);
        persist(false, panelWidth);
    }, [panelWidth, persist]);

    const toggle = useCallback(() => {
        setIsOpen((prev) => {
            const next = !prev;
            persist(next, panelWidth);
            return next;
        });
    }, [panelWidth, persist]);

    useEffect(() => {
        if (!isResizing) return;

        const onMove = (event: MouseEvent) => {
            const nextWidth = clampWidth(window.innerWidth - event.clientX - 16);
            setPanelWidth(nextWidth);
        };

        const onUp = () => {
            setIsResizing(false);
        };

        window.addEventListener('mousemove', onMove);
        window.addEventListener('mouseup', onUp);

        return () => {
            window.removeEventListener('mousemove', onMove);
            window.removeEventListener('mouseup', onUp);
        };
    }, [isResizing]);

    useEffect(() => {
        persist(isOpen, panelWidth);
    }, [isOpen, panelWidth, persist]);

    const beginResize = useCallback(() => {
        setIsResizing(true);
    }, []);

    const desktopLayout = useMemo(
        () => ({
            chatStyle: isOpen ? ({ width: `calc(100% - ${panelWidth + 8}px)` } as const) : ({ width: '100%' } as const),
            panelStyle: { width: `${panelWidth}px` } as const,
        }),
        [isOpen, panelWidth]
    );

    return {
        isOpen,
        panelWidth,
        isResizing,
        open,
        close,
        toggle,
        beginResize,
        desktopLayout,
    };
}
