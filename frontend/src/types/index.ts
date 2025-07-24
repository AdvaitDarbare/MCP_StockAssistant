export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  isLoading?: boolean;
}

export interface StockData {
  symbol: string;
  price: number;
  change: number;
  changePercent: number;
  volume: number;
  high: number;
  low: number;
  open: number;
}

export interface ApiResponse {
  response: string;
  error?: string;
}

export interface ChatState {
  messages: Message[];
  isLoading: boolean;
  error?: string;
}