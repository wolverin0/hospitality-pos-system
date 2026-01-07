
import React from 'react';
import { TicketLineItem as ILineItem } from '@/types/ticket.types';
import { clsx } from 'clsx';
import { CheckCircle2, Circle } from 'lucide-react';

interface TicketLineItemProps {
  item: ILineItem;
  onClick?: () => void;
}

export const TicketLineItem: React.FC<TicketLineItemProps> = ({ item, onClick }) => {
  const isCompleted = item.status === 'COMPLETED';
  const isVoided = item.status === 'VOIDED';

  return (
    <div 
      className={clsx(
        "flex items-start gap-3 py-2 border-b border-gray-700/50 last:border-0",
        isVoided && "opacity-50 line-through grayscale"
      )}
      onClick={onClick}
    >
      <div className="pt-1">
        {isCompleted ? (
          <CheckCircle2 size={18} className="text-green-500" />
        ) : (
          <Circle size={18} className="text-gray-600" />
        )}
      </div>
      
      <div className="flex-1">
        <div className="flex justify-between items-start">
          <span className={clsx(
            "font-bold text-lg leading-tight",
            isCompleted ? "text-gray-400" : "text-gray-100"
          )}>
            {item.quantity}x {item.name}
          </span>
        </div>

        {item.modifiers.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-1">
            {item.modifiers.map((mod, idx) => (
              <span 
                key={idx} 
                className="text-xs px-1.5 py-0.5 bg-gray-700 rounded text-red-300 font-medium"
              >
                {mod}
              </span>
            ))}
          </div>
        )}

        {item.special_instructions && (
          <p className="text-yellow-400 text-sm mt-1 italic font-medium bg-yellow-900/20 p-1 rounded">
            Note: {item.special_instructions}
          </p>
        )}
      </div>
    </div>
  );
};
