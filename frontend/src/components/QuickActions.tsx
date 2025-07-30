import React from 'react';
import { TrendingUp, BarChart3, Clock, Building2, Newspaper, Users } from 'lucide-react';

interface QuickActionsProps {
  onActionClick: (message: string) => void;
  isLoading: boolean;
}

const quickActions = [
  {
    icon: TrendingUp,
    label: "Stock Price",
    message: "What's AAPL stock price?",
    color: "text-green-600 bg-green-50 border-green-200"
  },
  {
    icon: BarChart3,
    label: "Compare Stocks", 
    message: "Compare AAPL vs GOOGL vs MSFT",
    color: "text-blue-600 bg-blue-50 border-blue-200"
  },
  {
    icon: Clock,
    label: "Market Hours",
    message: "What are market hours today?",
    color: "text-purple-600 bg-purple-50 border-purple-200"
  },
  {
    icon: Building2,
    label: "Company Info",
    message: "Tell me about Apple company",
    color: "text-orange-600 bg-orange-50 border-orange-200"
  },
  {
    icon: Newspaper,
    label: "Latest News",
    message: "Recent news for Tesla",
    color: "text-cyan-600 bg-cyan-50 border-cyan-200"
  },  
  {
    icon: Users,
    label: "Insider Trading",
    message: "Show me insider trading for NVDA",
    color: "text-pink-600 bg-pink-50 border-pink-200"
  }
];

export function QuickActions({ onActionClick, isLoading }: QuickActionsProps) {
  return (
    <div className="mb-6">
      <h3 className="text-sm font-medium text-gray-700 mb-3">Quick Actions</h3>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
        {quickActions.map((action, index) => {
          const Icon = action.icon;
          return (
            <button
              key={index}
              onClick={() => onActionClick(action.message)}
              disabled={isLoading}
              className={`
                p-3 rounded-lg border transition-all duration-200 text-left
                hover:shadow-sm disabled:opacity-50 disabled:cursor-not-allowed
                ${action.color}
              `}
            >
              <div className="flex items-center gap-2 mb-1">
                <Icon className="w-4 h-4" />
                <span className="text-sm font-medium">{action.label}</span>
              </div>
              <p className="text-xs opacity-75 line-clamp-1">
                {action.message}
              </p>
            </button>
          );
        })}
      </div>
    </div>
  );
}