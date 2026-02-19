import { render, screen, fireEvent } from '@testing-library/react';
import { ReportResultCard } from '../report-result-card';

// Mock the MarkdownRenderer component to simplify the DOM and avoid testing its internals here
jest.mock('@/components/markdown-renderer', () => ({
    MarkdownRenderer: ({ content }: { content: string }) => <div data-testid="markdown-content">{content}</div>,
}));

describe('ReportResultCard', () => {
    const mockReport = {
        id: 'test-report-1',
        report_type: 'goldman_screener',
        title: 'Test Report Title',
        generated_at: '2023-01-01T00:00:00Z',
        data: {},
        markdown: '# Hello World',
        generation_ms: 1250,
        quality_gate: {
            score: 0.85,
            warnings: ['Test warning'],
            passed: true,
            reasoning: 'Good'
        },
        sources_used: ['source-1', 'source-2'],
        tool_plan: [{ tool: 'tool-A', reason: 'reason A' }, { tool: 'tool-B', reason: 'reason B' }],
        effective_prompt: 'System prompt goes here',
    };

    it('renders the report title and generation time', () => {
        render(<ReportResultCard report={mockReport as any} />);
        expect(screen.getByText('Test Report Title')).toBeInTheDocument();
        expect(screen.getByText('1250 ms')).toBeInTheDocument();
    });

    it('renders the markdown content via MarkdownRenderer', () => {
        render(<ReportResultCard report={mockReport as any} />);
        expect(screen.getByTestId('markdown-content')).toHaveTextContent('# Hello World');
    });

    it('toggles the metadata section when clicked', () => {
        render(<ReportResultCard report={mockReport as any} />);

        // Initially closed
        expect(screen.queryByText(/Sources:/)).not.toBeInTheDocument();

        // Click to open
        const toggleButton = screen.getByRole('button', { name: /Sources & tool plan/i });
        fireEvent.click(toggleButton);

        // Should be visible
        expect(screen.getByText(/source-1, source-2/)).toBeInTheDocument();
        expect(screen.getByText(/tool-A, tool-B/)).toBeInTheDocument();
        expect(screen.getByText(/Test warning/)).toBeInTheDocument();
        expect(screen.getByText(/System prompt goes here/)).toBeInTheDocument();

        // Click to close
        fireEvent.click(toggleButton);

        // Should be closed
        expect(screen.queryByText(/Sources:/)).not.toBeInTheDocument();
    });

    it('handles reports without optional metadata', () => {
        const minimalReport = {
            id: 'minimal',
            report_type: 'basic',
            title: 'Minimal',
            generated_at: '2023-01-01',
            data: {},
            markdown: 'test',
        };

        render(<ReportResultCard report={minimalReport as any} />);

        const toggleButton = screen.getByRole('button', { name: /Sources & tool plan/i });
        fireEvent.click(toggleButton);

        // Sources and tool_plan are undefined, it should fallback gracefully
        const fallbackSource = screen.getAllByText('Not declared');
        expect(fallbackSource.length).toBeGreaterThan(0);
    });
});
