import React from 'react';
import { Plus, BarChart3 } from 'lucide-react';

interface SidebarProps {
  onNewChat: () => void;
}

export function Sidebar({ onNewChat }: SidebarProps) {
  return (
    <div className="w-64 h-full bg-gray-900 text-white flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-700">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-gradient-to-br from-blue-500 to-purple-600">
            <BarChart3 className="w-5 h-5 text-white" />
          </div>
          <h1 className="text-lg font-semibold">AI Stock Assistant</h1>
        </div>
        
        <button
          onClick={onNewChat}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg border border-gray-600 hover:bg-gray-800 transition-colors duration-200"
        >
          <Plus className="w-4 h-4" />
          New chat
        </button>
      </div>

      {/* Chat History (placeholder for future) */}
      <div className="flex-1 p-4">
        <div className="text-sm text-gray-400 mb-3">Recent</div>
        <div className="space-y-2">
          {/* Placeholder for chat history */}
          <div className="text-sm text-gray-500 italic">No previous chats</div>
        </div>
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-gray-700">
        <div className="text-xs text-gray-400">
          Market Intelligence Platform
        </div>
      </div>
    </div>
  );
}