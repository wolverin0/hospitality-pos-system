
import { Course, Station } from '@gastown/types';

export type TicketStatus = 'NEW' | 'PENDING' | 'PREPARING' | 'READY' | 'COMPLETED' | 'CANCELLED' | 'VOIDED';
export type LineItemStatus = 'PENDING' | 'STARTED' | 'COMPLETED' | 'VOIDED';

export interface TicketLineItem {
  id: string;
  ticket_id: string;
  menu_item_id: string;
  name: string;
  quantity: number;
  status: LineItemStatus;
  course: Course;
  station: Station | string;
  modifiers: string[];
  special_instructions?: string;
  created_at: string;
}

export interface Ticket {
  id: string;
  table_number: string;
  server_name: string;
  status: TicketStatus;
  priority: 'NORMAL' | 'RUSH';
  created_at: string;
  updated_at: string;
  items: TicketLineItem[];
  notes?: string;
  course_name?: string; // Derived or primary course
}

export interface StationFilter {
  id: string;
  name: string;
  type: Station | string;
  count: number;
}

export type WebSocketEvent = 
  | { type: 'TicketCreated'; payload: Ticket }
  | { type: 'TicketUpdated'; payload: Ticket }
  | { type: 'TicketFired'; payload: { ticketId: string } }
  | { type: 'TicketHeld'; payload: { ticketId: string } }
  | { type: 'TicketVoided'; payload: { ticketId: string } }
  | { type: 'TicketCompleted'; payload: { ticketId: string } };
