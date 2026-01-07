
import { useQuery } from '@tanstack/react-query';
import { Ticket } from '@/types/ticket.types';
import { useStationFilter } from './useStationFilter';

// Mock data generator for development until backend is ready
const generateMockTickets = (station: string | null): Ticket[] => {
  // In production with real API, this would never run if fetchTickets calls API
  // But for safety:
  // if (import.meta.env.PROD) return [];
  
  const statuses = ['NEW', 'PENDING', 'PREPARING', 'READY'] as const;
  const courses = ['APPETIZERS', 'MAINS', 'DESSERT'] as const;

  return Array.from({ length: 8 }).map((_, i) => ({
    id: `ticket-${i + 1}`,
    table_number: `${Math.floor(Math.random() * 20) + 1}`,
    server_name: ['Sarah', 'Mike', 'Jessica', 'Tom'][Math.floor(Math.random() * 4)],
    status: statuses[Math.floor(Math.random() * statuses.length)],
    priority: Math.random() > 0.8 ? 'RUSH' : 'NORMAL',
    created_at: new Date(Date.now() - Math.random() * 30 * 60000).toISOString(),
    updated_at: new Date().toISOString(),
    course_name: courses[Math.floor(Math.random() * courses.length)],
    items: [
      {
        id: `item-${i}-1`,
        ticket_id: `ticket-${i + 1}`,
        menu_item_id: '123',
        name: 'Burger',
        quantity: 1,
        status: 'PENDING',
        course: 'MAINS' as any,
        station: 'KITCHEN',
        modifiers: ['No onions', 'Extra cheese'],
        created_at: new Date().toISOString()
      },
      {
        id: `item-${i}-2`,
        ticket_id: `ticket-${i + 1}`,
        menu_item_id: '124',
        name: 'Fries',
        quantity: 1,
        status: 'PENDING',
        course: 'MAINS' as any,
        station: 'FRYER',
        modifiers: [],
        created_at: new Date().toISOString()
      }
    ]
  }));
};

const fetchTickets = async (station: string | null): Promise<Ticket[]> => {
  // TODO: Replace with actual API call
  // const params = new URLSearchParams();
  // if (station) params.append('station', station);
  // const res = await fetch(`/api/tickets?${params.toString()}`);
  // if (!res.ok) throw new Error('Failed to fetch tickets');
  // return res.json();
  
  // Return mock data for now to ensure UI can be built
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve(generateMockTickets(station));
    }, 500);
  });
};

export const useTickets = () => {
  const { selectedStation } = useStationFilter();

  return useQuery({
    queryKey: ['tickets', selectedStation],
    queryFn: () => fetchTickets(selectedStation),
    refetchInterval: 10000, // Fallback polling
  });
};
