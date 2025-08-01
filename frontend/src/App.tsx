import React, { useEffect, useRef } from 'react';
import { Header } from './components/Header';
import { Message } from './components/Message';
import { TypingIndicator } from './components/TypingIndicator';
import { MessageInput } from './components/MessageInput';
import { QuickActions } from './components/QuickActions';
import { useChat } from './hooks/useChat';

function App() {
  const { messages, isLoading, sendMessage, clearMessages } = useChat();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const showQuickActions = messages.length <= 1 && !isLoading;

  return (
    <div className="flex flex-col h-screen" style={{background: 'linear-gradient(to bottom right, var(--whisper-white), var(--light-fog))', color: 'var(--graphite-gray)'}}>
      {/* Subtle grain texture overlay */}
      <div className="absolute inset-0 opacity-[0.015] bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KICA8ZGVmcz4KICAgIDxmaWx0ZXIgaWQ9Im5vaXNlRmlsdGVyIj4KICAgICAgPGZlVHVyYnVsZW5jZSBiYXNlRnJlcXVlbmN5PSIwLjkiIG51bU9jdGF2ZXM9IjEiIHNlZWQ9IjEiLz4KICAgIDwvZmlsdGVyPgogIDwvZGVmcz4KICA8cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWx0ZXI9InVybCgjbm9pc2VGaWx0ZXIpIiBvcGFjaXR5PSIwLjMiLz4KPC9zdmc+')] pointer-events-none"></div>
      
      <Header onClearChat={clearMessages} />
      
      <main className="flex-1 overflow-y-auto relative">
        <div className="max-w-4xl mx-auto px-6 py-8">
          {showQuickActions && (
            <QuickActions onActionClick={sendMessage} isLoading={isLoading} />
          )}
          
          <div className="space-y-0">
            {messages.map((message) => (
              <Message 
                key={message.id} 
                message={message} 
                onFollowUpClick={sendMessage}
                isLoading={isLoading}
              />
            ))}
            
            {isLoading && <TypingIndicator />}
            
            <div ref={messagesEndRef} />
          </div>
        </div>
      </main>
      
      <MessageInput onSendMessage={sendMessage} isLoading={isLoading} />
    </div>
  );
}

export default App;