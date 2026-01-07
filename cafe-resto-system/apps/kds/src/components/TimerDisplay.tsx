
import React, { useEffect, useState } from 'react';
import { differenceInSeconds } from 'date-fns';
import { twMerge } from 'tailwind-merge';
import { Clock } from 'lucide-react';

interface TimerDisplayProps {
  startTime: string;
  className?: string;
}

export const TimerDisplay: React.FC<TimerDisplayProps> = ({ startTime, className }) => {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const updateTimer = () => {
      const start = new Date(startTime);
      const now = new Date();
      setElapsed(differenceInSeconds(now, start));
    };

    updateTimer();
    const interval = setInterval(updateTimer, 1000);
    return () => clearInterval(interval);
  }, [startTime]);

  const formatTime = (seconds: number) => {
    if (seconds < 0) return "00:00";
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    
    if (mins >= 60) {
      const hours = Math.floor(mins / 60);
      const remainingMins = mins % 60;
      return `${hours}h ${remainingMins}m`;
    }
    
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const getTimerColor = (seconds: number) => {
    if (seconds > 600) return 'text-red-400 animate-pulse font-bold'; // > 10 mins
    if (seconds > 300) return 'text-yellow-400'; // > 5 mins
    return 'text-green-400';
  };

  return (
    <div className={twMerge('flex items-center gap-1 font-mono', getTimerColor(elapsed), className)}>
      <Clock size={14} />
      <span>{formatTime(elapsed)}</span>
    </div>
  );
};
