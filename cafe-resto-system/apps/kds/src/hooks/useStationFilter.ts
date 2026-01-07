
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { Station } from '@gastown/types';

interface StationFilterState {
  selectedStation: string | null;
  setStation: (station: string | null) => void;
}

export const useStationFilter = create<StationFilterState>()(
  persist(
    (set) => ({
      selectedStation: null,
      setStation: (station) => set({ selectedStation: station }),
    }),
    {
      name: 'kds-station-filter',
    }
  )
);
