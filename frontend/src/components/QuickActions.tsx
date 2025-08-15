import React from 'react';
import { DollarSign, BarChart3, Clock, Building2, Newspaper, Users, MessageCircle, TrendingUp, Star } from 'lucide-react';

interface QuickActionsProps {
  onActionClick: (message: string) => void;
  isLoading: boolean;
  onOpenRedditDashboard?: () => void;
}

const quickActions = [
  {
    icon: DollarSign,
    iconColor: "text-blue-400",
    label: "Stock Price",
    message: "What's AAPL stock price?",
    description: "What's AAPL stock price?"
  },
  {
    icon: BarChart3,
    iconColor: "text-teal-400", 
    label: "Compare Stocks",
    message: "Compare AAPL vs GOOGL vs MSFT",
    description: "Compare AAPL vs GOOGL vs MSFT"
  },
  {
    icon: Clock,
    iconColor: "text-emerald-400",
    label: "Market Hours",
    message: "What are market hours today?",
    description: "What are market hours today?"
  },
  {
    icon: Building2,
    iconColor: "text-cyan-400",
    label: "Company Info",
    message: "Tell me about Apple company", 
    description: "Tell me about Apple company"
  },
  {
    icon: Newspaper,
    iconColor: "text-amber-400",
    label: "Latest News",
    message: "Recent news for Tesla",
    description: "Recent news for Tesla"
  },
  {
    icon: Users,
    iconColor: "text-indigo-400",
    label: "Insider Trading", 
    message: "Show me insider trading for NVDA",
    description: "Show me insider trading for NVDA"
  },
  {
    icon: TrendingUp,
    iconColor: "text-green-400",
    label: "Should I Buy?",
    message: "Should I buy NVDA stock?",
    description: "Should I buy NVDA stock?"
  },
  {
    icon: Star,
    iconColor: "text-purple-400",
    label: "Analyst Ratings",
    message: "Analyst ratings for META",
    description: "Analyst ratings for META"
  }
];

export function QuickActions({ onActionClick, isLoading, onOpenRedditDashboard }: QuickActionsProps) {
  return (
    <div className="mb-12">
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold mb-3 tracking-tight" style={{fontFamily: 'Space Grotesk, Inter, system-ui, sans-serif', color: 'var(--graphite-gray)'}}>
          Market Intelligence at Your Fingertips
        </h2>
        <p className="text-lg font-light" style={{color: 'var(--misty-gray)'}}>Explore stocks, analyze trends, and make informed decisions</p>
      </div>
      
      <div className="grid grid-cols-4 gap-4">
        {quickActions.map((action, index) => {
          const Icon = action.icon;
          return (
            <button
              key={index}
              onClick={() => onActionClick(action.message)}
              disabled={isLoading}
              className="backdrop-blur-sm border rounded-xl p-4 text-left hover:scale-[1.02] transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed group shadow-lg hover:shadow-xl min-h-[110px] flex flex-col justify-between"
              style={{
                backgroundColor: 'var(--whisper-white)',
                borderColor: 'var(--misty-gray)',
                opacity: 0.9
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
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <div className="w-7 h-7 rounded-lg flex items-center justify-center border" style={{background: 'linear-gradient(to bottom right, var(--light-fog), var(--whisper-white))', borderColor: 'var(--misty-gray)'}}>
                    <Icon className={`w-4 h-4 ${action.iconColor}`} />
                  </div>
                  <span className="font-semibold text-sm" style={{color: 'var(--graphite-gray)'}}>{action.label}</span>
                </div>
                <p className="text-xs leading-relaxed group-hover:opacity-80" style={{color: 'var(--misty-gray)'}}>
                  {action.description}
                </p>  
              </div>
            </button>
          );
        })}
      </div>

      {/* Reddit Pulse Button */}
      {onOpenRedditDashboard && (
        <div className="mt-8 flex justify-center">
          <button
            onClick={onOpenRedditDashboard}
            disabled={isLoading}
            className="backdrop-blur-sm border rounded-xl p-5 text-center hover:scale-[1.02] transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed group shadow-lg hover:shadow-xl"
            style={{
              backgroundColor: 'var(--whisper-white)',
              borderColor: 'var(--misty-gray)',
              opacity: 0.9,
              background: 'linear-gradient(135deg, rgba(147, 51, 234, 0.05), rgba(59, 130, 246, 0.05))'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = 'rgba(147, 51, 234, 0.1)';
              e.currentTarget.style.borderColor = '#9333ea';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'var(--whisper-white)';
              e.currentTarget.style.borderColor = 'var(--misty-gray)';
            }}
          >
            <div className="flex items-center gap-4 mb-2">
              <div className="w-10 h-10 rounded-lg flex items-center justify-center border" style={{background: 'linear-gradient(135deg, #9333ea, #3b82f6)', borderColor: 'var(--misty-gray)'}}>
                <MessageCircle className="w-5 h-5 text-white" />
              </div>
              <div className="text-left">
                <span className="font-bold text-lg block" style={{color: 'var(--graphite-gray)'}}>Reddit Market Pulse</span>
                <span className="text-sm" style={{color: 'var(--misty-gray)'}}>Live discussions from stock communities</span>
              </div>
            </div>
            <p className="text-sm leading-relaxed group-hover:opacity-80 mt-2" style={{color: 'var(--misty-gray)'}}>
              Monitor trending discussions, sentiment, and hot topics from Reddit's top investing communities including r/wallstreetbets, r/stocks, and r/investing
            </p>
          </button>
        </div>
      )}
    </div>
  );
}