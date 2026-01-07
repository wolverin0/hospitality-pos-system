
import React from 'react';
import { Ticket } from '@/types/ticket.types';
import { TicketCard } from './TicketCard';
import { Inbox } from 'lucide-react';

interface TicketQueueProps {
  tickets: Ticket[];
  loading?: boolean;
}

export const TicketQueue: React.FC<TicketQueueProps> = ({ tickets, loading }) => {
  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (tickets.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-gray-500 opacity-50">
        <Inbox size={64} className="mb-4" />
        <p className="text-xl font-medium">No active tickets</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 pb-20">
      {tickets.map((ticket) => (
        <div key={ticket.id} className="h-[400px]">
          <TicketCard ticket={ticket} />
        </div>
      ))}
    </div>
  );
};
