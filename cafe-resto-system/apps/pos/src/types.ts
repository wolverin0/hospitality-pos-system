export interface Order {
  id: string
  table_session_id: string
  server_id: string
  status: string
  created_at: string
  completed_at: string | null
  cancelled_at: string | null
  subtotal: number
  tax_amount: number
  discount_amount: number
  service_charge: number
  total_amount: number
  tip_amount: number
  guest_count: number | null
  special_requests: string | null
  order_notes: string | null
  is_rush: boolean
  priority_level: number | null
  version: number
}

export interface OrderLineItem {
  id: string
  order_id: string
  menu_item_id: string | null
  name: string
  description: string | null
  quantity: number
  unit_price: number
  price_at_order: number
  line_total: number
  special_instructions: string | null
  preparation_status: string
  is_voided: boolean
  is_comped: boolean
  discount_amount: number
}

export interface Payment {
  id: string
  order_id: string
  payment_intent_id: string | null
  amount: number
  currency: string
  method: string
  status: string
  created_at: string
  updated_at: string | null
  processed_at: string | null
  failed_at: string | null
  refunded_at: string | null
  card_last_4: string | null
  card_holder_name: string | null
  terminal_reference_id: string | null
  qr_code: string | null
  processing_fee: number | null
}

export interface CartItem {
  id: string
  cartId: string
  name: string
  quantity: number
  price: number
}

export interface Category {
  id: string
  name: string
}

export interface MenuItem {
  id: string
  name: string
  price: number
  category_id: string
}
