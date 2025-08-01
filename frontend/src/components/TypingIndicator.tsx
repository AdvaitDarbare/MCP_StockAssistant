import React from 'react';
import { Bot } from 'lucide-react';

export function TypingIndicator() {
  return (
    <div className="flex gap-3 justify-start mb-6">
      <div className="flex-shrink-0 w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
        <Bot className="w-5 h-5 text-white" />
      </div>
      
      <div className="message-assistant">
        <div className="typing-indicator">
          <div className="typing-dot" style={{ '--delay': 0 } as React.CSSProperties}></div>
          <div className="typing-dot" style={{ '--delay': 1 } as React.CSSProperties}></div>
          <div className="typing-dot" style={{ '--delay': 2 } as React.CSSProperties}></div>
        </div>
      </div>
    </div>
  );
}