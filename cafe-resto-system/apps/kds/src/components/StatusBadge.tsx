
import React from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { TicketStatus } from '@/types/ticket.types';

interface StatusBadgeProps {
  status: TicketStatus;
  className?: string;
}

const statusConfig: Record<TicketStatus, { color: string; label: string }> = {
  NEW: { color: 'bg-gray-700 text-gray-300 border-gray-600', label: 'NEW' },
  PENDING: { color: 'bg-yellow-900/50 text-yellow-200 border-yellow-700', label: 'PENDING' },
  PREPARING: { color: 'bg-blue-900/50 text-blue-200 border-blue-700', label: 'PREP' },
  READY: { color: 'bg-green-900/50 text-green-200 border-green-700', label: 'READY' },
  COMPLETED: { color: 'bg-purple-900/50 text-purple-200 border-purple-700', label: 'DONE' },
  CANCELLED: { color: 'bg-red-900/50 text-red-200 border-red-700', label: 'CANCEL' },
  VOIDED: { color: 'bg-red-900/50 text-red-200 border-red-700', label: 'VOID' },
};

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, className }) => {
  const config = statusConfig[status] || statusConfig.NEW;

  return (
    <span
      className={twMerge(
        'px-2.5 py-0.5 rounded-full text-xs font-bold border tracking-wider',
        config.color,
        className
      )}
    >
      {config.label}
    </span>
  );
};
