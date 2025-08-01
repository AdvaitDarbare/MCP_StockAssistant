import React, { useState, useRef, KeyboardEvent } from 'react';
import { Send, Loader2 } from 'lucide-react';

interface MessageInputProps {
  onSendMessage: (message: string) => void;
  isLoading: boolean;
}

export function MessageInput({ onSendMessage, isLoading }: MessageInputProps) {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = () => {
    if (message.trim() && !isLoading) {
      onSendMessage(message);
      setMessage('');
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setMessage(e.target.value);
    
    // Auto-resize textarea
    const textarea = e.target;
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
  };

  return (
    <div className="sticky bottom-0 backdrop-blur-xl border-t p-6" style={{backgroundColor: 'var(--whisper-white)', borderColor: 'var(--misty-gray)', opacity: 0.95}}>
      <div className="max-w-4xl mx-auto">
        <div className="relative flex items-end gap-4 backdrop-blur-sm rounded-2xl border p-4 shadow-2xl" style={{backgroundColor: 'var(--light-fog)', borderColor: 'var(--misty-gray)'}} onFocus={(e) => {
            e.currentTarget.style.boxShadow = '0 0 0 2px rgba(74, 85, 104, 0.2)';
            e.currentTarget.style.borderColor = 'var(--slate-blue)';
          }}>
          <textarea
            ref={textareaRef}
            value={message}
            onChange={handleTextareaChange}
            onKeyDown={handleKeyDown}
            placeholder="Real-time quotes • Historical data • Company insights • Market analysis..."
            className="flex-1 resize-none bg-transparent border-none outline-none px-3 py-3 max-h-[120px] min-h-[40px] text-base leading-relaxed" style={{color: 'var(--graphite-gray)'}}
            rows={1}
            disabled={isLoading}
          />
          
          <button
            onClick={handleSubmit}
            disabled={!message.trim() || isLoading}
            className="flex-shrink-0 p-3 text-white rounded-xl transition-all duration-200 shadow-lg hover:shadow-xl hover:scale-105 disabled:cursor-not-allowed disabled:opacity-50" style={{background: 'linear-gradient(to bottom right, var(--slate-blue), #667eea)'}}
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>
        
        <div className="text-center mt-3">
          <p className="text-xs font-medium" style={{color: 'var(--misty-gray)'}}>
            Press <kbd className="px-2 py-1 rounded text-xs border" style={{backgroundColor: 'var(--light-fog)', color: 'var(--graphite-gray)', borderColor: 'var(--misty-gray)'}}>Enter</kbd> to send • <kbd className="px-2 py-1 rounded text-xs border" style={{backgroundColor: 'var(--light-fog)', color: 'var(--graphite-gray)', borderColor: 'var(--misty-gray)'}}>Shift + Enter</kbd> for new line
          </p>
        </div>
      </div>
    </div>
  );
}