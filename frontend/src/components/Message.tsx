import React from 'react';
import { Message as MessageType } from '../types';
import { User, Bot } from 'lucide-react';
import { FollowUpSuggestions } from './FollowUpSuggestions';

interface MessageProps {
  message: MessageType;
  onFollowUpClick?: (message: string) => void;
  isLoading?: boolean;
}

export function Message({ message, onFollowUpClick, isLoading = false }: MessageProps) {
  const isUser = message.role === 'user';

  // Extract follow-up suggestions from the content
  const extractFollowUps = (content: string): { content: string; suggestions: string[] } => {
    const followUpMatch = content.match(/__FOLLOW_UPS_START__(.*?)__FOLLOW_UPS_END__/s);
    
    if (followUpMatch) {
      const followUpText = followUpMatch[1].trim();
      const suggestions = followUpText
        .split('\n')
        .filter(line => line.trim() && /^\d+\./.test(line.trim()))
        .map(line => line.trim());
      
      // Remove the follow-up section from the main content
      const cleanContent = content.replace(/__FOLLOW_UPS_START__(.*?)__FOLLOW_UPS_END__/s, '').trim();
      
      return { content: cleanContent, suggestions };
    }
    
    return { content, suggestions: [] };
  };

  const { content: cleanContent, suggestions } = extractFollowUps(message.content);

  // Format the message content to handle markdown-like formatting
  const formatContent = (content: string) => {
    // Convert markdown-style formatting to HTML
    let formatted = content
      // Bold text **text** -> <strong>text</strong>
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      // Italic text *text* -> <em>text</em>  
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      // Code blocks ```code``` -> <pre><code>code</code></pre>
      .replace(/```(.*?)```/gs, '<pre class="code-block"><code>$1</code></pre>')
      // Inline code `code` -> <code>code</code>
      .replace(/`([^`]+)`/g, '<code class="bg-gray-100 px-1 py-0.5 rounded text-sm">$1</code>')
      // Line breaks
      .replace(/\n/g, '<br />');

    return formatted;
  };

  return (
    <div className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'} mb-6`}>
      {!isUser && (
        <div className="flex-shrink-0 w-8 h-8 bg-primary-500 rounded-full flex items-center justify-center">
          <Bot className="w-5 h-5 text-white" />
        </div>
      )}
      
      <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} max-w-4xl`}>
        <div className={isUser ? 'message-user' : 'message-assistant'}>
          <div 
            className={`prose ${isUser ? 'prose-invert' : ''} prose-sm max-w-none`}
            dangerouslySetInnerHTML={{ __html: formatContent(cleanContent) }}
          />
        </div>
        
        {/* Render follow-up suggestions as buttons */}
        {!isUser && suggestions.length > 0 && onFollowUpClick && (
          <div className="w-full mt-3">
            <FollowUpSuggestions
              suggestions={suggestions}
              onSuggestionClick={onFollowUpClick}
              isLoading={isLoading}
            />
          </div>
        )}
        
        <div className="text-xs text-gray-500 mt-1 px-1">
          {message.timestamp.toLocaleTimeString([], { 
            hour: '2-digit', 
            minute: '2-digit' 
          })}
        </div>
      </div>

      {isUser && (
        <div className="flex-shrink-0 w-8 h-8 bg-gray-700 rounded-full flex items-center justify-center">
          <User className="w-5 h-5 text-white" />
        </div>
      )}
    </div>
  );
}