import React, { useState, useEffect } from 'react';
import { MessageCircle, TrendingUp, Users, ExternalLink, RefreshCw, X } from 'lucide-react';

interface RedditPost {
  id: string;
  title: string;
  subreddit: string;
  author: string;
  score: number;
  upvote_ratio: number;
  num_comments: number;
  created_time: string;
  url: string;
  selftext: string;
  symbols: string[];
  sentiment: {
    score: number;
    label: 'bullish' | 'bearish' | 'neutral';
    confidence: number;
  };
  is_trending: boolean;
}

interface SubredditActivity {
  name: string;
  display_name: string;
  subscribers: number;
  active_users: number;
  description: string;
  url: string;
}

interface DashboardData {
  trending_posts: RedditPost[];
  subreddit_activity: SubredditActivity[];
  last_updated: string;
}

interface RedditDashboardProps {
  isOpen: boolean;
  onClose: () => void;
}

export function RedditDashboard({ isOpen, onClose }: RedditDashboardProps) {
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const response = await fetch('http://localhost:8000/reddit/dashboard');
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();
      
      if (result.success) {
        setDashboardData(result.data);
        setError(null);
      } else {
        throw new Error('Failed to fetch dashboard data');
      }
    } catch (err) {
      console.error('Error fetching Reddit dashboard data:', err);
      setError('Failed to load Reddit data. Please try again.');
    } finally {
      setLoading(false);
    }
  };


  useEffect(() => {
    if (isOpen) {
      fetchDashboardData();
      // Auto-refresh every 5 minutes
      const interval = setInterval(fetchDashboardData, 5 * 60 * 1000);
      return () => clearInterval(interval);
    }
  }, [isOpen]);


  const formatTime = (timeString: string) => {
    try {
      const date = new Date(timeString);
      const now = new Date();
      const diffInHours = (now.getTime() - date.getTime()) / (1000 * 60 * 60);
      
      if (diffInHours < 1) {
        const minutes = Math.floor(diffInHours * 60);
        return `${minutes}m ago`;
      } else if (diffInHours < 24) {
        return `${Math.floor(diffInHours)}h ago`;
      } else {
        return `${Math.floor(diffInHours / 24)}d ago`;
      }
    } catch {
      return 'Unknown';
    }
  };

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case 'bullish': return '#10b981'; // green
      case 'bearish': return '#ef4444'; // red
      default: return '#6b7280'; // gray
    }
  };

  const formatNumber = (num: number) => {
    if (num >= 1000000) {
      return `${(num / 1000000).toFixed(1)}M`;
    } else if (num >= 1000) {
      return `${(num / 1000).toFixed(1)}K`;
    }
    return num.toString();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed top-0 right-0 h-full w-[28rem] bg-white shadow-2xl z-40 border-l border-gray-200 flex flex-col">
      {/* Dashboard Panel */}
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MessageCircle className="w-5 h-5" />
            <div>
              <h2 className="text-lg font-bold">Reddit Pulse</h2>
              <p className="text-xs text-blue-100">Live market discussions</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={fetchDashboardData}
              disabled={loading}
              className="p-1 bg-white bg-opacity-20 rounded hover:bg-opacity-30 transition-all"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={onClose}
              className="p-1 bg-white bg-opacity-20 rounded hover:bg-opacity-30 transition-all"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-3">
        {loading && !dashboardData ? (
          <div className="flex items-center justify-center h-32">
            <div className="text-center">
              <RefreshCw className="w-6 h-6 animate-spin mx-auto text-blue-600 mb-2" />
              <p className="text-sm text-gray-600">Loading...</p>
            </div>
          </div>
        ) : error ? (
          <div className="text-center p-4">
            <p className="text-red-600 text-sm mb-3">{error}</p>
            <button
              onClick={fetchDashboardData}
              className="px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
            >
              Try Again
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Trending Posts */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <TrendingUp className="w-4 h-4 text-orange-600" />
                <h3 className="font-semibold text-gray-900 text-sm">Trending</h3>
                <span className="text-xs text-gray-500">
                  {dashboardData?.trending_posts.length}
                </span>
              </div>
              <div className="space-y-2">
                {dashboardData?.trending_posts.slice(0, 10).map((post) => (
                  <div key={post.id} className="border rounded p-3 hover:bg-gray-50 text-xs">
                    <div className="flex items-start gap-2 mb-2">
                      <span className="bg-blue-100 text-blue-800 px-1.5 py-0.5 rounded text-xs font-medium">
                        r/{post.subreddit}
                      </span>
                      {post.symbols.length > 0 && (
                        <div className="flex gap-1">
                          {post.symbols.slice(0, 2).map((symbol) => (
                            <span key={symbol} className="bg-yellow-100 text-yellow-800 px-1 py-0.5 rounded text-xs font-mono">
                              ${symbol}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    <h4 className="text-sm font-medium text-gray-900 mb-2 line-clamp-2">
                      {post.title}
                    </h4>
                    <div className="flex items-center justify-between text-xs text-gray-500">
                      <div className="flex items-center gap-3">
                        <span>↑ {formatNumber(post.score)}</span>
                        <span>💬 {formatNumber(post.num_comments)}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span>{formatTime(post.created_time)}</span>
                        <a
                          href={post.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-gray-400 hover:text-blue-600"
                        >
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Active Communities */}
            {dashboardData?.subreddit_activity && (
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <Users className="w-4 h-4 text-purple-600" />
                  <h3 className="font-semibold text-gray-900 text-sm">Communities</h3>
                </div>
                <div className="space-y-3">
                  {dashboardData.subreddit_activity.slice(0, 6).map((subreddit) => (
                    <div key={subreddit.name} className="p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors border border-gray-100">
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex-1 min-w-0">
                          <div className="font-semibold text-gray-900 text-sm mb-1">r/{subreddit.name}</div>
                          <div className="text-xs text-gray-600 mb-2">
                            {formatNumber(subreddit.subscribers)} members
                          </div>
                        </div>
                        <a
                          href={subreddit.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="ml-2 p-1.5 bg-white rounded hover:bg-blue-50 text-gray-400 hover:text-blue-600 transition-colors"
                        >
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      </div>
                      <p className="text-xs text-gray-500 leading-relaxed line-clamp-2">
                        {subreddit.description}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function PostCard({ post, formatNumber, formatTime }: { 
  post: RedditPost;
  formatNumber: (num: number) => string;
  formatTime: (timeString: string) => string;
}) {
  return (
    <div className="border rounded-lg p-4 hover:bg-gray-50 transition-colors">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded font-medium">
              r/{post.subreddit}
            </span>
            <span 
              className="text-xs px-2 py-1 rounded font-medium"
              style={{ 
                backgroundColor: post.sentiment.label === 'bullish' ? '#dcfce7' : 
                                post.sentiment.label === 'bearish' ? '#fef2f2' : '#f3f4f6',
                color: post.sentiment.label === 'bullish' ? '#166534' : 
                       post.sentiment.label === 'bearish' ? '#dc2626' : '#374151'
              }}
            >
              {post.sentiment.label}
            </span>
            {post.symbols.length > 0 && (
              <div className="flex gap-1">
                {post.symbols.slice(0, 3).map((symbol) => (
                  <span key={symbol} className="text-xs bg-yellow-100 text-yellow-800 px-1 py-0.5 rounded font-mono">
                    ${symbol}
                  </span>
                ))}
              </div>
            )}
          </div>
          
          <h4 className="font-medium text-gray-900 text-sm mb-2 line-clamp-2">
            {post.title}
          </h4>
          
          <div className="flex items-center gap-4 text-xs text-gray-500">
            <span>↑ {formatNumber(post.score)}</span>
            <span>💬 {formatNumber(post.num_comments)}</span>
            <span>{formatTime(post.created_time)}</span>
          </div>
        </div>
        
        <a
          href={post.url}
          target="_blank"
          rel="noopener noreferrer"
          className="p-1 text-gray-400 hover:text-blue-600 flex-shrink-0"
        >
          <ExternalLink className="w-4 h-4" />
        </a>
      </div>
    </div>
  );
}