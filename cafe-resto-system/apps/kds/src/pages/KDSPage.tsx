
import React from 'react';
import { useTickets } from '@/hooks/useTickets';
import { useTicketSocket } from '@/hooks/useTicketSocket';
import { StationFilter } from '@/components/StationFilter';
import { TicketQueue } from '@/components/TicketQueue';
import { Wifi, WifiOff, ChefHat } from 'lucide-react';
import { clsx } from 'clsx';

export const KDSPage: React.FC = () => {
  const { data: tickets = [], isLoading } = useTickets();
  const { isConnected } = useTicketSocket();

  // Calculate stats
  const pendingCount = tickets.filter(t => t.status === 'PENDING').length;
  const preparingCount = tickets.filter(t => t.status === 'PREPARING').length;
  const completedCount = tickets.filter(t => t.status === 'READY').length;

  return (
    <div className="flex flex-col h-screen bg-background text-white overflow-hidden">
      {/* Top Bar */}
      <header className="bg-surface border-b border-gray-700 p-2 flex items-center justify-between shrink-0 h-16">
        <div className="flex items-center gap-4 flex-1 overflow-hidden">
          <div className="flex items-center gap-2 px-3 py-1 bg-gray-900 rounded-lg shrink-0">
            <ChefHat className="text-orange-500" />
            <span className="font-black text-lg tracking-wider">GASTOWN<span className="text-orange-500">KDS</span></span>
          </div>
          
          <div className="flex-1 overflow-hidden">
            <StationFilter />
          </div>
        </div>

        <div className="flex items-center gap-4 px-4 shrink-0">
          <div className={clsx(
            "flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider",
            isConnected ? "bg-green-900/50 text-green-400" : "bg-red-900/50 text-red-400 animate-pulse"
          )}>
            {isConnected ? <Wifi size={14} /> : <WifiOff size={14} />}
            {isConnected ? "ONLINE" : "OFFLINE"}
          </div>
          
          <div className="w-10 h-10 bg-gray-700 rounded-full flex items-center justify-center border border-gray-600">
            <span className="font-bold text-sm">KS</span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto p-4 hide-scrollbar">
        <TicketQueue tickets={tickets} loading={isLoading} />
      </main>

      {/* Bottom Status Bar */}
      <footer className="bg-surface border-t border-gray-700 p-2 grid grid-cols-3 gap-4 shrink-0 h-14">
        <div className="flex items-center justify-between px-4 py-1 bg-gray-800 rounded text-yellow-500">
          <span className="font-bold text-xs uppercase tracking-wider">Pending</span>
          <span className="text-2xl font-black">{pendingCount}</span>
        </div>
        <div className="flex items-center justify-between px-4 py-1 bg-gray-800 rounded text-blue-500">
          <span className="font-bold text-xs uppercase tracking-wider">Working</span>
          <span className="text-2xl font-black">{preparingCount}</span>
        </div>
        <div className="flex items-center justify-between px-4 py-1 bg-gray-800 rounded text-green-500">
          <span className="font-bold text-xs uppercase tracking-wider">Ready</span>
          <span className="text-2xl font-black">{completedCount}</span>
        </div>
      </footer>
    </div>
  );
};
