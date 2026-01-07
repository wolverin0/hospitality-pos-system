import { PaymentIntent, Payment, Refund } from '../types'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

export interface PaymentIntent {
  id: string
  order_id: string
  amount: number
  currency: string
  method: string
  status: string
  client_secret: string | null
  payment_intent_reference: string | null
  created_at: string
  updated_at: string | null
  processed_at: string | null
  failed_at: string | null
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

export interface Refund {
  id: string
  tenant_id: string
  original_payment_id: string
  order_id: string
  amount: number
  currency: string
  status: string
  reason_code: string
  reason: string
  created_by: string
  processed_by: string | null
  authorized_by: string | null
  refund_reference_id: string | null
  external_refund_id: string | null
  created_at: string
  processed_at: string | null
}

export interface PaymentIntentCreate {
  order_id: string
  amount: number
  method: string
}

export interface PaymentCreate {
  order_id: string
  amount: number
  method: string
  card_last_4?: string
  card_holder_name?: string
  terminal_reference_id?: string
  qr_code?: string
}

export interface RefundCreate {
  payment_id: string
  order_id: string
  amount: number
  reason_code: string
  reason: string
}

export async function createPaymentIntent(token: string, data: PaymentIntentCreate): Promise<PaymentIntent> {
  const response = await fetch(\`\${API_BASE_URL}/payments/intents\`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': \`Bearer \${token}\`
    },
    body: JSON.stringify(data)
  })

  if (!response.ok) {
    throw new Error(\`Payment intent creation failed: \${response.statusText}\`)
  }

  return await response.json()
}

export async function processPayment(token: string, data: PaymentCreate): Promise<Payment> {
  const response = await fetch(\`\${API_BASE_URL}/payments/process\`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': \`Bearer \${token}\`
    },
    body: JSON.stringify(data)
  })

  if (!response.ok) {
    throw new Error(\`Payment processing failed: \${response.statusText}\`)
  }

  return await response.json()
}

export async function listPayments(token: string, params?: {
  order_id?: string
  payment_method?: string
  payment_status?: string
  date_from?: string
  date_to?: string
  skip?: number
  limit?: number
}): Promise<Payment[]> {
  const url = new URL(\`\${API_BASE_URL}/payments/\`)
  const queryParams = new URLSearchParams()

  if (params?.order_id) queryParams.set('order_id', params.order_id)
  if (params?.payment_method) queryParams.set('payment_method', params.payment_method)
  if (params?.payment_status) queryParams.set('payment_status', params.payment_status)
  if (params?.date_from) queryParams.set('date_from', params.date_from)
  if (params?.date_to) queryParams.set('date_to', params.date_to)
  if (params?.skip) queryParams.set('skip', params.skip.toString())
  if (params?.limit) queryParams.set('limit', params.limit.toString())

  const response = await fetch(\`\${url}\?${queryParams.toString()}`, {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': \`Bearer \${token}\`
    }
  })

  if (!response.ok) {
    throw new Error(\`Failed to fetch payments: \${response.statusText}\`)
  }

  return response.json()
}

export async function getPayment(token: string, paymentId: string): Promise<Payment> {
  const response = await fetch(\`\${API_BASE_URL}/payments/\${paymentId}\`, {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': \`Bearer \${token}\`
    }
  })

  if (!response.ok) {
    throw new Error(\`Failed to fetch payment: \${response.statusText}\`)
  }

  return response.json()
}

export async function updatePayment(token: string, paymentId: string, data: any): Promise<Payment> {
  const response = await fetch(\`\${API_BASE_URL}/payments/\${paymentId}\`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': \`Bearer \${token}\`
    },
    body: JSON.stringify(data)
  })

  if (!response.ok) {
    throw new Error(\`Payment update failed: \${response.statusText}\`)
  }

  return response.json()
}

export async function processRefund(token: string, paymentId: string, data: RefundCreate): Promise<Refund> {
  const response = await fetch(\`\${API_BASE_URL}/payments/\${paymentId}/refund\`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': \`Bearer \${token}\`
    },
    body: JSON.stringify(data)
  })

  if (!response.ok) {
    throw new Error(\`Refund processing failed: \${response.statusText}\`)
  }

  return response.json()
}

export async function createSplitPayment(token: string, orderId: string, payments: PaymentCreate[]): Promise<Payment[]> {
  const response = await fetch(\`\${API_BASE_URL}/payments/split\`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': \`Bearer \${token}\`
    },
    body: JSON.stringify({
      order_id: orderId,
      payments
    })
  })

  if (!response.ok) {
    throw new Error(\`Split payment failed: \${response.statusText}\`)
  }

  return response.json()
}
