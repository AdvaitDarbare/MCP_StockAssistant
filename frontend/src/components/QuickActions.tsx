import React from 'react';
import { DollarSign, BarChart3, Clock, Building2, Newspaper, Users } from 'lucide-react';

interface QuickActionsProps {
  onActionClick: (message: string) => void;
  isLoading: boolean;
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
  }
];

export function QuickActions({ onActionClick, isLoading }: QuickActionsProps) {
  return (
    <div className="mb-12">
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold mb-3 tracking-tight" style={{fontFamily: 'Space Grotesk, Inter, system-ui, sans-serif', color: 'var(--graphite-gray)'}}>
          Market Intelligence at Your Fingertips
        </h2>
        <p className="text-lg font-light" style={{color: 'var(--misty-gray)'}}>Explore stocks, analyze trends, and make informed decisions</p>
      </div>
      
      <div className="grid grid-cols-3 gap-5">
        {quickActions.map((action, index) => {
          const Icon = action.icon;
          return (
            <button
              key={index}
              onClick={() => onActionClick(action.message)}
              disabled={isLoading}
              className="backdrop-blur-sm border rounded-xl p-5 text-left hover:scale-[1.02] transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed group shadow-lg hover:shadow-xl min-h-[120px] flex flex-col justify-between"
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
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-8 h-8 rounded-lg flex items-center justify-center border" style={{background: 'linear-gradient(to bottom right, var(--light-fog), var(--whisper-white))', borderColor: 'var(--misty-gray)'}}>
                    <Icon className={`w-4 h-4 ${action.iconColor}`} />
                  </div>
                  <span className="font-semibold text-base" style={{color: 'var(--graphite-gray)'}}>{action.label}</span>
                </div>
                <p className="text-sm leading-relaxed group-hover:opacity-80" style={{color: 'var(--misty-gray)'}}>
                  {action.description}
                </p>  
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}