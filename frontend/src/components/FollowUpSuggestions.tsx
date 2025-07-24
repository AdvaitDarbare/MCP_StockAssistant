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
      color: "text-green-600 bg-green-50 border-green-200"
    };
  }
  
  if (suggestion.includes('📊') || lower.includes('compare') || lower.includes('analyst')) {
    return {
      icon: BarChart3,
      color: "text-blue-600 bg-blue-50 border-blue-200"
    };
  }
  
  if (suggestion.includes('📉') || lower.includes('history') || lower.includes('performance')) {
    return {
      icon: Activity,
      color: "text-red-600 bg-red-50 border-red-200"
    };
  }
  
  if (suggestion.includes('🚀') || lower.includes('movers') || lower.includes('gainers')) {
    return {
      icon: PieChart,
      color: "text-emerald-600 bg-emerald-50 border-emerald-200"
    };
  }
  
  if (suggestion.includes('🕐') || lower.includes('hours') || lower.includes('market')) {
    return {
      icon: Clock,
      color: "text-purple-600 bg-purple-50 border-purple-200"
    };
  }
  
  if (suggestion.includes('🏢') || lower.includes('company') || lower.includes('overview')) {
    return {
      icon: Building2,
      color: "text-orange-600 bg-orange-50 border-orange-200"
    };
  }
  
  if (suggestion.includes('📰') || lower.includes('news') || lower.includes('articles')) {
    return {
      icon: Newspaper,
      color: "text-cyan-600 bg-cyan-50 border-cyan-200"
    };
  }
  
  if (suggestion.includes('👥') || lower.includes('insider') || lower.includes('trading')) {
    return {
      icon: Users,
      color: "text-pink-600 bg-pink-50 border-pink-200"
    };
  }
  
  // Default fallback
  return {
    icon: Search,
    color: "text-gray-600 bg-gray-50 border-gray-200"
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
      <h4 className="text-sm font-medium text-gray-700 mb-3">💡 Suggested Follow-ups</h4>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
        {suggestions.map((suggestion, index) => {
          const { icon: Icon, color } = getIconAndColor(suggestion);
          const label = getLabel(suggestion);
          const cleanText = cleanSuggestionText(suggestion);
          
          return (
            <button
              key={index}
              onClick={() => onSuggestionClick(cleanText)}
              disabled={isLoading}
              className={`
                p-3 rounded-lg border transition-all duration-200 text-left
                hover:shadow-sm hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed
                ${color}
              `}
            >
              <div className="flex items-center gap-2 mb-1">
                <Icon className="w-4 h-4" />
                <span className="text-sm font-medium">{label}</span>
              </div>
              <p className="text-xs opacity-75 line-clamp-2">
                {cleanText}
              </p>
            </button>
          );
        })}
      </div>
    </div>
  );
}