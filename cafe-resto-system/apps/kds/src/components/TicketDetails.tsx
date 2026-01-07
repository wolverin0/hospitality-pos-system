
import React from 'react';
import { Ticket } from '@/types/ticket.types';
import { X, Printer } from 'lucide-react';
import { TicketLineItem } from './TicketLineItem';
import { StatusBadge } from './StatusBadge';
import { TimerDisplay } from './TimerDisplay';
import { ActionButtons } from './ActionButtons';

interface TicketDetailsProps {
  ticket: Ticket;
  onClose: () => void;
}

export const TicketDetails: React.FC<TicketDetailsProps> = ({ ticket, onClose }) => {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-surface w-full max-w-2xl rounded-2xl shadow-2xl overflow-hidden border border-gray-700 flex flex-col max-h-[90vh]">
        
        {/* Modal Header */}
        <div className="p-6 bg-gray-800 border-b border-gray-700 flex justify-between items-start">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h2 className="text-4xl font-black text-white">Table {ticket.table_number}</h2>
              <StatusBadge status={ticket.status} className="text-sm px-3 py-1" />
            </div>
            <div className="flex gap-4 text-gray-400">
              <span>Server: <span className="text-white font-medium">{ticket.server_name}</span></span>
              <span>Ticket #{ticket.id}</span>
              <TimerDisplay startTime={ticket.created_at} className="text-lg" />
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-2 hover:bg-gray-700 rounded-full text-gray-400 hover:text-white transition-colors"
          >
            <X size={32} />
          </button>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto p-6 bg-[#1a1a2a]">
          {ticket.notes && (
            <div className="mb-6 bg-yellow-900/20 border border-yellow-700/50 p-4 rounded-lg">
              <span className="text-yellow-500 font-bold uppercase text-xs tracking-wider block mb-1">Ticket Notes</span>
              <p className="text-yellow-200 text-lg">{ticket.notes}</p>
            </div>
          )}

          <div className="space-y-4">
            {ticket.items.map((item) => (
              <TicketLineItem key={item.id} item={item} />
            ))}
          </div>
        </div>

        {/* Footer Actions */}
        <div className="p-6 bg-gray-800 border-t border-gray-700 grid grid-cols-2 gap-4">
          <div>
            <button className="flex items-center gap-2 px-6 py-4 bg-gray-700 hover:bg-gray-600 rounded-lg text-white font-bold transition-colors w-full justify-center">
              <Printer size={20} />
              Reprint Ticket
            </button>
          </div>
          <div>
            <ActionButtons 
              status={ticket.status}
              onBump={() => { console.log('Bump', ticket.id); onClose(); }}
              onHold={() => { console.log('Hold', ticket.id); }}
              onFire={() => { console.log('Fire', ticket.id); }}
              onVoid={() => { console.log('Void', ticket.id); }}
            />
          </div>
        </div>
      </div>
    </div>
  );
};
