import React, { useState, useEffect } from 'react';
import { BarChart3, RefreshCw, Trash2 } from 'lucide-react';

interface HeaderProps {
  onClearChat: () => void;
}

export function Header({ onClearChat }: HeaderProps) {
  const [currentTime, setCurrentTime] = useState(new Date());
  const [isMarketOpen, setIsMarketOpen] = useState(false);

  useEffect(() => {
    const timer = setInterval(() => {
      const now = new Date();
      setCurrentTime(now);
      
      // Market hours: 9:30 AM - 4:00 PM ET, Monday-Friday
      const easternTime = new Date(now.toLocaleString("en-US", {timeZone: "America/New_York"}));
      const day = easternTime.getDay(); // 0 = Sunday, 1 = Monday, etc.
      const hours = easternTime.getHours();
      const minutes = easternTime.getMinutes();
      const totalMinutes = hours * 60 + minutes;
      
      // Market is open Monday (1) to Friday (5), 9:30 AM to 4:00 PM ET
      const isWeekday = day >= 1 && day <= 5;
      const marketOpenTime = 9 * 60 + 30; // 9:30 AM in minutes
      const marketCloseTime = 16 * 60; // 4:00 PM in minutes
      const isWithinMarketHours = totalMinutes >= marketOpenTime && totalMinutes < marketCloseTime;
      
      setIsMarketOpen(isWeekday && isWithinMarketHours);
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true
    });
  };

  return (
    <header className="sticky top-0 z-10 backdrop-blur-xl border-b px-4 py-3" style={{backgroundColor: 'var(--whisper-white)', borderColor: 'var(--misty-gray)', opacity: 0.95}}>
      <div className="max-w-4xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="w-11 h-11 rounded-xl flex items-center justify-center shadow-lg" style={{background: 'linear-gradient(to bottom right, var(--slate-blue), #667eea)'}}>
            <BarChart3 className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight" style={{fontFamily: 'Space Grotesk, Inter, system-ui, sans-serif', color: 'var(--graphite-gray)'}}>
              AI Stock Assistant
            </h1>
            <p className="text-sm font-medium" style={{color: 'var(--misty-gray)'}}>Market Intelligence Platform</p>
          </div>
        </div>
        
        <div className="flex items-center gap-4">
          <div className="text-right">
            <div className="font-mono text-lg font-semibold" style={{color: 'var(--graphite-gray)'}}>{formatTime(currentTime)}</div>
            <div className="text-xs px-2 py-1 rounded-md font-medium border" style={{
              backgroundColor: isMarketOpen ? 'rgba(104, 211, 145, 0.2)' : 'rgba(252, 129, 129, 0.2)',
              color: isMarketOpen ? 'var(--sage-green)' : 'var(--dusty-coral)',
              borderColor: isMarketOpen ? 'var(--sage-green)' : 'var(--dusty-coral)'
            }}>
              Market {isMarketOpen ? 'Open' : 'Closed'}
            </div>
          </div>
          
          <div className="flex items-center gap-2 px-3 py-1.5 border rounded-lg text-sm font-medium" style={{backgroundColor: 'rgba(74, 85, 104, 0.1)', color: 'var(--slate-blue)', borderColor: 'var(--slate-blue)'}}>
            <div className="w-2 h-2 rounded-full animate-pulse shadow-sm" style={{backgroundColor: 'var(--slate-blue)', boxShadow: '0 0 4px rgba(74, 85, 104, 0.5)'}}></div>
            Live
          </div>
        </div>
      </div>
    </header>
  );
}