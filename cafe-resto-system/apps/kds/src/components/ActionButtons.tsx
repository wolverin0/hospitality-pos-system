
import React from 'react';
import { CheckCircle2, PauseCircle, Flame, XCircle } from 'lucide-react';

interface ActionButtonsProps {
  onBump?: () => void;
  onHold?: () => void;
  onFire?: () => void;
  onVoid?: () => void;
  size?: 'sm' | 'lg';
  status?: string;
}

export const ActionButtons: React.FC<ActionButtonsProps> = ({ 
  onBump, 
  onHold, 
  onFire, 
  onVoid,
  size = 'lg',
  status
}) => {
  const isHeld = status === 'HELD';
  const isCompleted = status === 'COMPLETED';

  if (isCompleted) return null;

  return (
    <div className={`grid grid-cols-4 gap-2 ${size === 'sm' ? 'h-10' : 'h-14'}`}>
      {/* Bump Button - Primary Action */}
      <button
        onClick={onBump}
        className="col-span-1 bg-green-700 hover:bg-green-600 active:bg-green-800 text-white rounded-lg flex items-center justify-center transition-colors"
        title="Bump Ticket"
      >
        <CheckCircle2 size={size === 'sm' ? 18 : 24} />
      </button>

      {/* Hold Button */}
      <button
        onClick={onHold}
        disabled={isHeld}
        className={`col-span-1 flex items-center justify-center rounded-lg transition-colors ${
          isHeld 
            ? 'bg-gray-700 text-gray-500 cursor-not-allowed' 
            : 'bg-yellow-700 hover:bg-yellow-600 active:bg-yellow-800 text-white'
        }`}
        title="Hold Ticket"
      >
        <PauseCircle size={size === 'sm' ? 18 : 24} />
      </button>

      {/* Fire Button */}
      <button
        onClick={onFire}
        className="col-span-1 bg-blue-700 hover:bg-blue-600 active:bg-blue-800 text-white rounded-lg flex items-center justify-center transition-colors"
        title="Fire Ticket"
      >
        <Flame size={size === 'sm' ? 18 : 24} />
      </button>

      {/* Void Button */}
      <button
        onClick={onVoid}
        className="col-span-1 bg-red-900/80 hover:bg-red-800 active:bg-red-900 text-white rounded-lg flex items-center justify-center transition-colors border border-red-700"
        title="Void Ticket"
      >
        <XCircle size={size === 'sm' ? 18 : 24} />
      </button>
    </div>
  );
};
