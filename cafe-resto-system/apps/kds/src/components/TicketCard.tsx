
import React, { useState } from 'react';
import { Ticket } from '@/types/ticket.types';
import { clsx } from 'clsx';
import { StatusBadge } from './StatusBadge';
import { CourseBadge } from './CourseBadge';
import { TimerDisplay } from './TimerDisplay';
import { TicketLineItem } from './TicketLineItem';
import { ActionButtons } from './ActionButtons';
import { TicketDetails } from './TicketDetails';

interface TicketCardProps {
  ticket: Ticket;
}

export const TicketCard: React.FC<TicketCardProps> = ({ ticket }) => {
  const [showDetails, setShowDetails] = useState(false);

  const isRush = ticket.priority === 'RUSH';

  return (
    <>
      <div 
        className={clsx(
          "flex flex-col h-full rounded-xl overflow-hidden bg-surface transition-transform duration-200",
          "border-l-4 shadow-xl",
          isRush ? "border-l-red-500 shadow-red-900/20" : "border-l-blue-500",
          ticket.status === 'COMPLETED' && "opacity-50 grayscale"
        )}
      >
        {/* Header */}
        <div className="p-3 bg-gray-800/50 border-b border-gray-700 flex justify-between items-start">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-2xl font-black text-white">T-{ticket.table_number}</span>
              {isRush && <span className="animate-pulse text-xs font-bold bg-red-600 text-white px-1 rounded">RUSH</span>}
            </div>
            <div className="text-xs text-gray-400 font-medium uppercase tracking-wider">
              {ticket.server_name}
            </div>
          </div>
          <div className="flex flex-col items-end gap-1">
            <TimerDisplay startTime={ticket.created_at} />
            <StatusBadge status={ticket.status} />
          </div>
        </div>

        {/* Course Header */}
        {ticket.course_name && (
          <div className="px-3 py-1 bg-gray-900/30 border-b border-gray-700 flex justify-between items-center">
            <CourseBadge course={ticket.course_name} />
            <span className="text-[10px] text-gray-500">#{ticket.id.slice(-4)}</span>
          </div>
        )}

        {/* Items */}
        <div 
          className="flex-1 p-3 overflow-y-auto space-y-1 min-h-[160px] cursor-pointer hover:bg-white/5 transition-colors"
          onClick={() => setShowDetails(true)}
        >
          {ticket.items.map((item) => (
            <TicketLineItem key={item.id} item={item} />
          ))}
        </div>

        {/* Actions Footer */}
        <div className="p-2 border-t border-gray-700 bg-gray-800/30">
          <ActionButtons 
            status={ticket.status}
            onBump={() => console.log('Bump', ticket.id)}
            onHold={() => console.log('Hold', ticket.id)}
            onFire={() => console.log('Fire', ticket.id)}
            onVoid={() => console.log('Void', ticket.id)}
            size="lg"
          />
        </div>
      </div>

      {showDetails && (
        <TicketDetails 
          ticket={ticket} 
          onClose={() => setShowDetails(false)} 
        />
      )}
    </>
  );
};
