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
    <div className="flex flex-col h-screen bg-gray-50">
      <Header onClearChat={clearMessages} />
      
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-4 py-6">
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