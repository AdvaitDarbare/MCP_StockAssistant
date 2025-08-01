import React from 'react';
import { TrendingUp, BarChart3, Clock, Building2, Newspaper, Users, Activity, PieChart, Search } from 'lucide-react';

interface FollowUpSuggestionsProps {
  suggestions: string[];
  onSuggestionClick: (message: string) => void;
  isLoading: boolean;
}

// Map emoji patterns to icons and colors
const getIconAndColor = (suggestion: string) => {
  const lower = suggestion.toLowerCase();
  
  if (suggestion.includes('📈') || lower.includes('price') || lower.includes('quote')) {
    return {
      icon: TrendingUp,
      color: "text-blue-400 bg-blue-500/20 border-blue-500/30 hover:bg-blue-500/30"
    };
  }
  
  if (suggestion.includes('📊') || lower.includes('compare') || lower.includes('analyst')) {
    return {
      icon: BarChart3,
      color: "text-teal-400 bg-teal-500/20 border-teal-500/30 hover:bg-teal-500/30"
    };
  }
  
  if (suggestion.includes('📉') || lower.includes('history') || lower.includes('performance')) {
    return {
      icon: Activity,
      color: "text-cyan-400 bg-cyan-500/20 border-cyan-500/30 hover:bg-cyan-500/30"
    };
  }
  
  if (suggestion.includes('🚀') || lower.includes('movers') || lower.includes('gainers')) {
    return {
      icon: PieChart,
      color: "text-emerald-400 bg-emerald-500/20 border-emerald-500/30 hover:bg-emerald-500/30"
    };
  }
  
  if (suggestion.includes('🕐') || lower.includes('hours') || lower.includes('market')) {
    return {
      icon: Clock,
      color: "text-indigo-400 bg-indigo-500/20 border-indigo-500/30 hover:bg-indigo-500/30"
    };
  }
  
  if (suggestion.includes('🏢') || lower.includes('company') || lower.includes('overview')) {
    return {
      icon: Building2,
      color: "text-cyan-400 bg-cyan-500/20 border-cyan-500/30 hover:bg-cyan-500/30"
    };
  }
  
  if (suggestion.includes('📰') || lower.includes('news') || lower.includes('articles')) {
    return {
      icon: Newspaper,
      color: "text-amber-400 bg-amber-500/20 border-amber-500/30 hover:bg-amber-500/30"
    };
  }
  
  if (suggestion.includes('👥') || lower.includes('insider') || lower.includes('trading')) {
    return {
      icon: Users,
      color: "text-indigo-400 bg-indigo-500/20 border-indigo-500/30 hover:bg-indigo-500/30"
    };
  }
  
  // Default fallback
  return {
    icon: Search,
    color: "text-slate-400 bg-slate-500/20 border-slate-500/30 hover:bg-slate-500/30"
  };
};

// Clean up suggestion text (remove emojis and numbers)
const cleanSuggestionText = (suggestion: string): string => {
  return suggestion
    .replace(/^\d+\.\s*/, '') // Remove "1. " prefix
    .replace(/[📈📊📉🚀🕐🏢📰👥⚖️🔍]/g, '') // Remove emojis
    .trim();
};

// Extract a short label from the suggestion
const getLabel = (suggestion: string): string => {
  const cleaned = cleanSuggestionText(suggestion);
  
  // Extract key action words
  if (cleaned.toLowerCase().includes('analyst')) return 'Analyst Ratings';
  if (cleaned.toLowerCase().includes('news')) return 'Recent News';
  if (cleaned.toLowerCase().includes('insider')) return 'Insider Trading';
  if (cleaned.toLowerCase().includes('compare')) return 'Compare Stocks';
  if (cleaned.toLowerCase().includes('price') && !cleaned.toLowerCase().includes('history')) return 'Stock Price';
  if (cleaned.toLowerCase().includes('history')) return 'Price History';
  if (cleaned.toLowerCase().includes('gainers') || cleaned.toLowerCase().includes('movers')) return 'Market Movers';
  if (cleaned.toLowerCase().includes('hours')) return 'Market Hours';
  if (cleaned.toLowerCase().includes('company') || cleaned.toLowerCase().includes('overview')) return 'Company Info';
  if (cleaned.toLowerCase().includes('analysis')) return 'Full Analysis';
  
  // Fallback: use first few words
  const words = cleaned.split(' ').slice(0, 2);
  return words.join(' ');
};

export function FollowUpSuggestions({ suggestions, onSuggestionClick, isLoading }: FollowUpSuggestionsProps) {
  if (suggestions.length === 0) return null;

  return (
    <div className="mt-4 mb-2">
      <h4 className="text-sm font-medium mb-3" style={{color: 'var(--misty-gray)'}}>💡 Suggested Follow-ups</h4>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
        {suggestions.map((suggestion, index) => {
          const { icon: Icon, color } = getIconAndColor(suggestion);
          const label = getLabel(suggestion);
          const cleanText = cleanSuggestionText(suggestion);
          
          return (
            <button
              key={index}
              onClick={() => onSuggestionClick(cleanText)}
              disabled={isLoading}
              className="p-3 rounded-lg border transition-all duration-200 text-left disabled:opacity-50 disabled:cursor-not-allowed"
              style={{
                backgroundColor: 'var(--whisper-white)',
                borderColor: 'var(--misty-gray)'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = 'var(--light-fog)';
                e.currentTarget.style.borderColor = 'var(--slate-blue)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'var(--whisper-white)';
                e.currentTarget.style.borderColor = 'var(--misty-gray)';
              }}
            >
              <div className="flex items-center gap-2 mb-1">
                <Icon className="w-4 h-4" style={{color: 'var(--slate-blue)'}} />
                <span className="text-sm font-medium" style={{fontFamily: 'Space Grotesk, Inter, system-ui, sans-serif', color: 'var(--graphite-gray)'}}>{label}</span>
              </div>
              <p className="text-xs opacity-75 line-clamp-1" style={{color: 'var(--misty-gray)'}}>
                {cleanText}
              </p>
            </button>
          );
        })}
      </div>
    </div>
  );
}