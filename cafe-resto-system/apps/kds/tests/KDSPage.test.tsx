
import { render, screen, fireEvent } from '@testing-library/react';
import { KDSPage } from '../src/pages/KDSPage';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi } from 'vitest';

// Mock dependencies
vi.mock('@/hooks/useTicketSocket', () => ({
  useTicketSocket: () => ({ isConnected: true })
}));

// Setup QueryClient for tests
const createTestQueryClient = () => new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
    },
  },
});

describe('KDSPage', () => {
  it('renders station filter', () => {
    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <KDSPage />
      </QueryClientProvider>
    );
    
    expect(screen.getByText('ALL')).toBeInTheDocument();
    expect(screen.getByText('BAR')).toBeInTheDocument();
    expect(screen.getByText('KITCHEN')).toBeInTheDocument();
  });

  it('shows connection status', () => {
    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <KDSPage />
      </QueryClientProvider>
    );
    
    expect(screen.getByText('ONLINE')).toBeInTheDocument();
  });
});
