
import React from 'react';
import { useStationFilter } from '@/hooks/useStationFilter';
import { clsx } from 'clsx';
import { MonitorPlay } from 'lucide-react';

const STATIONS = [
  'ALL',
  'BAR',
  'KITCHEN',
  'GRILL',
  'FRYER',
  'SALAD',
  'DESSERT',
  'PREP',
  'SUSHI',
  'PIZZA'
];

export const StationFilter: React.FC = () => {
  const { selectedStation, setStation } = useStationFilter();

  const handleStationClick = (station: string) => {
    setStation(station === 'ALL' ? null : station);
  };

  const activeStation = selectedStation || 'ALL';

  return (
    <div className="flex overflow-x-auto pb-2 gap-2 hide-scrollbar">
      {STATIONS.map((station) => {
        const isActive = activeStation === station;
        return (
          <button
            key={station}
            onClick={() => handleStationClick(station)}
            className={clsx(
              'px-4 py-3 rounded-lg font-bold text-sm tracking-wide whitespace-nowrap transition-all',
              'flex items-center gap-2',
              isActive
                ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/50 scale-105'
                : 'bg-surface text-gray-400 hover:bg-gray-700 hover:text-white'
            )}
          >
            {isActive && <MonitorPlay size={16} />}
            {station}
          </button>
        );
      })}
    </div>
  );
};
