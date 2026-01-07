
import React from 'react';
import { useTickets } from '@/hooks/useTickets';
import { useTicketSocket } from '@/hooks/useTicketSocket';
import { TicketQueue } from '@/components/TicketQueue';
import { LayoutDashboard, Flame } from 'lucide-react';

export const ExpoPage: React.FC = () => {
  // Expo views ALL tickets
  const { data: tickets = [], isLoading } = useTickets();
  const { isConnected } = useTicketSocket();

  return (
    <div className="flex flex-col h-screen bg-background text-white">
      {/* Expo Header */}
      <header className="bg-indigo-950/30 border-b border-indigo-900/50 p-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <LayoutDashboard className="text-indigo-400" size={28} />
          <h1 className="text-2xl font-black tracking-tight">EXPO MODE</h1>
        </div>
        
        <div className="flex gap-3">
           <button className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg font-bold transition-colors">
             <Flame size={18} />
             Fire All Courses
           </button>
        </div>
      </header>

      {/* Content */}
      <main className="flex-1 overflow-y-auto p-4">
        <TicketQueue tickets={tickets} loading={isLoading} />
      </main>
    </div>
  );
};
