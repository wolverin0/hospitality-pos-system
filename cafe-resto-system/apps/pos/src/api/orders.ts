import { Order } from '../types'
import { createOrder, getOrder, listOrders, completeOrder, cancelOrder } from './orders'

// Order API client functions
export async function getOrders(token: string, params?: {
  table_session_id?: string
  server_id?: string
  order_status?: string
  date_from?: string
  date_to?: string
  skip?: number
  limit?: number
}): Promise<{ items: Order[], total: number, page: number, page_size: number }> {
  const response = await listOrders(token, params)
  return response
}

export async function getOrderById(token: string, orderId: string): Promise<Order> {
  const response = await getOrder(token, orderId)
  return response
}

export async function createNewOrder(token: string, data: any): Promise<Order> {
  const response = await createOrder(token, data)
  return response
}

export async function completeOrderById(token: string, orderId: string): Promise<Order> {
  const response = await completeOrder(token, orderId)
  return response
}

export async function cancelOrderById(token: string, orderId: string, reason: string): Promise<Order> {
  const response = await cancelOrder(token, orderId, reason)
  return response
}
