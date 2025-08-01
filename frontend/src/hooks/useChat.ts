import { useState, useCallback } from 'react';
import { Message, ChatState } from '../types';
import { sendMessage, ApiError } from '../utils/api';

// Generate smart follow-up suggestions based on user query and response content
const generateFallbackSuggestions = (userQuery: string, assistantResponse: string): string => {
  const query = userQuery.toLowerCase();
  const response = assistantResponse.toLowerCase();
  
  // Extract potential symbols from the response or query
  const symbolPattern = /\b[A-Z]{1,5}\b/g;
  const symbols = (userQuery + ' ' + assistantResponse).match(symbolPattern) || [];
  const uniqueSymbols = Array.from(new Set(symbols)).filter(s => s.length <= 5).slice(0, 3);
  const primarySymbol = uniqueSymbols[0] || 'AAPL';
  
  // Define all available tools and their descriptions
  const availableTools = [
    {
      category: 'advisor',
      tools: [
        { name: 'buy_recommendation', keywords: ['should i buy', 'should i invest', 'good investment', 'worth buying'], template: (symbol?: string) => `Should I buy ${symbol || 'AAPL'} stock?` },
        { name: 'risk_analysis', keywords: ['risk', 'risky', 'safe', 'volatile'], template: (symbol?: string) => `What are the risks of investing in ${symbol || 'AAPL'}?` },
        { name: 'investment_timing', keywords: ['when to buy', 'good time', 'timing', 'wait'], template: (symbol?: string) => `Is now a good time to buy ${symbol || 'AAPL'}?` },
        { name: 'investment_comparison', keywords: ['better investment', 'which to choose', 'compare for investment'], template: (symbol?: string) => `Compare ${symbol || 'AAPL'} vs GOOGL for investment` }
      ]
    },
    {
      category: 'stock',
      tools: [
        { name: 'stock_price', keywords: ['price', 'quote', 'current'], template: (symbol?: string) => `What's ${symbol || 'AAPL'} current stock price?` },
        { name: 'compare_stocks', keywords: ['compare', 'vs', 'versus'], template: (symbol?: string) => `Compare ${symbol || 'AAPL'} vs GOOGL vs MSFT` },
        { name: 'price_history', keywords: ['history', 'performance', 'chart', 'trend'], template: (symbol?: string) => `Show me 6 month price history for ${symbol || 'AAPL'}` },
        { name: 'market_movers', keywords: ['gainers', 'losers', 'movers', 'trending'], template: () => 'Top market gainers today' },
        { name: 'market_hours', keywords: ['hours', 'schedule', 'open', 'close'], template: () => 'What are market hours today?' }
      ]
    },
    {
      category: 'equity',
      tools: [
        { name: 'company_info', keywords: ['company', 'about', 'overview', 'profile'], template: (symbol?: string) => `Tell me about ${symbol || 'AAPL'} company` },
        { name: 'news', keywords: ['news', 'articles', 'headlines', 'recent'], template: (symbol?: string) => `Recent news for ${symbol || 'AAPL'}` },
        { name: 'analyst_ratings', keywords: ['analyst', 'rating', 'recommendation', 'target'], template: (symbol?: string) => `Analyst ratings for ${symbol || 'AAPL'}` },
        { name: 'insider_trading', keywords: ['insider', 'trading activity', 'transactions'], template: (symbol?: string) => `Insider trading activity for ${symbol || 'AAPL'}` }
      ]
    }
  ];
  
  const suggestions: string[] = [];
  
  // Check what tools haven't been used based on response content
  for (const category of availableTools) {
    for (const tool of category.tools) {
      const hasBeenUsed = tool.keywords.some(keyword => 
        response.includes(keyword) || 
        response.includes(tool.name.replace('_', ' ')) ||
        (category.category === 'stock' && response.includes('stock information')) ||
        (category.category === 'equity' && response.includes('company insights')) ||
        (category.category === 'advisor' && response.includes('investment advice'))
      );
      
      if (!hasBeenUsed) {
        // Generate suggestion based on available symbols or general query
        if (tool.name === 'market_movers' || tool.name === 'market_hours') {
          suggestions.push(tool.template());
        } else if (uniqueSymbols.length > 0) {
          suggestions.push(tool.template(primarySymbol));
        } else if (tool.name === 'stock_price' || tool.name === 'compare_stocks') {
          // For general queries without symbols, suggest popular stocks
          suggestions.push(tool.template('AAPL'));
        }
      }
    }
  }
  
  // If we have symbols but few suggestions, add cross-category suggestions
  if (uniqueSymbols.length > 0 && suggestions.length < 3) {
    const crossSuggestions = [
      `Compare ${primarySymbol} with other top stocks`,
      `Full analysis of ${primarySymbol}`,
      `What analysts think about ${primarySymbol}`,
      `${primarySymbol} vs competitors`
    ];
    
    for (const crossSugg of crossSuggestions) {
      if (suggestions.length < 4 && !suggestions.some(s => s.toLowerCase().includes(crossSugg.toLowerCase().split(' ')[0]))) {
        suggestions.push(crossSugg);
      }
    }
  }
  
  // If still no suggestions, add general market suggestions
  if (suggestions.length === 0) {
    suggestions.push(
      'What\'s AAPL stock price?',
      'Compare AAPL vs GOOGL vs MSFT', 
      'What are market hours today?',
      'Top market gainers today'
    );
  }
  
  // Add variety for different symbols if we have multiple
  if (uniqueSymbols.length > 1 && suggestions.length < 4) {
    for (let i = 1; i < uniqueSymbols.length && suggestions.length < 4; i++) {
      const altSymbol = uniqueSymbols[i];
      if (!suggestions.some(s => s.includes(altSymbol))) {
        suggestions.push(`What's ${altSymbol} stock price?`);
      }
    }
  }
  
  // Format as numbered list with dynamic emojis
  const formattedSuggestions = suggestions.slice(0, 4).map((suggestion, index) => {
    let emoji = '🔍';
    const suggLower = suggestion.toLowerCase();
    
    if (suggLower.includes('should i buy') || suggLower.includes('good investment')) emoji = '🎯';
    else if (suggLower.includes('risk') || suggLower.includes('risky')) emoji = '⚖️';
    else if (suggLower.includes('good time') || suggLower.includes('timing')) emoji = '⏰';
    else if (suggLower.includes('compare') && suggLower.includes('investment')) emoji = '🔍';
    else if (suggLower.includes('price') && !suggLower.includes('history')) emoji = '📈';
    else if (suggLower.includes('compare') || suggLower.includes('vs')) emoji = '📊';
    else if (suggLower.includes('history') || suggLower.includes('performance')) emoji = '📉';
    else if (suggLower.includes('company') || suggLower.includes('about') || suggLower.includes('analysis')) emoji = '🏢';
    else if (suggLower.includes('news') || suggLower.includes('articles')) emoji = '📰';
    else if (suggLower.includes('analyst') || suggLower.includes('rating')) emoji = '📊';
    else if (suggLower.includes('insider') || suggLower.includes('trading')) emoji = '👥';
    else if (suggLower.includes('gainers') || suggLower.includes('movers') || suggLower.includes('trending')) emoji = '🚀';
    else if (suggLower.includes('hours') || suggLower.includes('schedule')) emoji = '🕐';
    
    return `${index + 1}. ${emoji} ${suggestion}`;
  });
  
  return `\n\n__FOLLOW_UPS_START__\n${formattedSuggestions.join('\n')}\n__FOLLOW_UPS_END__`;
};

export function useChat(): ChatState & {
  sendMessage: (content: string) => Promise<void>;
  clearMessages: () => void;
} {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string>();

  const handleSendMessage = useCallback(async (content: string) => {
    if (!content.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: content.trim(),
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    setError(undefined);

    try {
      const response = await sendMessage(content.trim());
      
      // Check if response already contains follow-up suggestions
      let finalResponse = response;
      if (!response.includes('__FOLLOW_UPS_START__')) {
        // Generate fallback suggestions if none exist
        const fallbackSuggestions = generateFallbackSuggestions(content.trim(), response);
        finalResponse = response + fallbackSuggestions;
      }
      
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: finalResponse,
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (err) {
      const errorMessage = err instanceof ApiError ? err.message : 'An unexpected error occurred';
      setError(errorMessage);
      
      const errorResponse: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `❌ **Error**: ${errorMessage}\n\nPlease try again or check if the AI Stock Assistant server is running.`,
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, errorResponse]);
    } finally {
      setIsLoading(false);
    }
  }, [isLoading]);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(undefined);
  }, []);

  return {
    messages,
    isLoading,
    error,
    sendMessage: handleSendMessage,
    clearMessages,
  };
}