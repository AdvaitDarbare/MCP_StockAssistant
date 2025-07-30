import { useState, useCallback } from 'react';
import { Message, ChatState } from '../types';
import { sendMessage, ApiError } from '../utils/api';

export function useChat(): ChatState & {
  sendMessage: (content: string) => Promise<void>;
  clearMessages: () => void;
} {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: "Hello! I'm your AI Stock Assistant. I can help you with:\n\n📈 **Stock Prices & Quotes** - \"What's AAPL stock price?\"\n📊 **Stock Comparisons** - \"Compare AAPL vs TSLA\"\n📉 **Historical Performance** - \"NVDA performance last 6 months\"\n🚀 **Market Movers** - \"Show me top gainers today\"\n🕐 **Trading Hours** - \"What are market hours?\"\n🏢 **Company Information** - \"Tell me about Apple company\"\n📰 **Company News** - \"Recent news for Tesla\"\n👥 **Insider Trading** - \"Insider activity for NVDA\"\n📊 **Analyst Ratings** - \"Analyst ratings for AMD\"\n\nWhat would you like to know about the markets?",
      timestamp: new Date(),
    }
  ]);
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
      
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response,
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
    setMessages([
      {
        id: '1',
        role: 'assistant',
        content: "Hello! I'm your AI Stock Assistant. I can help you with:\n\n📈 **Stock Prices & Quotes** - \"What's AAPL stock price?\"\n📊 **Stock Comparisons** - \"Compare AAPL vs TSLA\"\n📉 **Historical Performance** - \"NVDA performance last 6 months\"\n🚀 **Market Movers** - \"Show me top gainers today\"\n🕐 **Trading Hours** - \"What are market hours?\"\n🏢 **Company Information** - \"Tell me about Apple company\"\n📰 **Company News** - \"Recent news for Tesla\"\n👥 **Insider Trading** - \"Insider activity for NVDA\"\n📊 **Analyst Ratings** - \"Analyst ratings for AMD\"\n\nWhat would you like to know about the markets?",
        timestamp: new Date(),
      }
    ]);
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