'use client'

import { useState } from 'react'
import { Trash2 as TrashIcon } from 'lucide-react'
import { Inter } from 'next/font/google'
import { CartItem } from './types'

interface CartPanelProps {
  cartItems: CartItem[]
  onRemoveFromCart: (cartId: number) => void
  onClearCart: () => void
  onCheckout: () => void
}

export function CartPanel({ cartItems, onRemoveFromCart, onClearCart, onCheckout }: CartPanelProps) {
  return (
    <div className="bg-gray-800 w-full p-4 flex flex-col">
      {/* Header */}
      <div className="mb-4 flex justify-between items-center">
        <h2 className="text-lg font-bold text-white">Cart</h2>
        <button
          onClick={onClearCart}
          className="text-red-400 hover:text-red-300 text-sm"
        >
          Clear Cart
        </button>
      </div>

      {/* Cart Items */}
      <div className="flex-1 overflow-y-auto space-y-3">
        {cartItems.map((item) => (
          <div
            key={item.cartId}
            className="bg-gray-700 rounded-lg p-3 flex justify-between items-center"
          >
            <div>
              <p className="font-medium text-white">{item.name}</p>
              <p className="text-sm text-gray-400">Qty: {item.quantity}</p>
              <p className="text-lg font-bold text-green-400">${(item.price * item.quantity).toFixed(2)}</p>
            </div>
            <button
              onClick={() => onRemoveFromCart(item.cartId)}
              className="text-red-400 hover:text-red-300"
            >
              <Trash2 className="w-5 h-5" />
            </button>
          </div>
        ))}
      </div>

      {/* Checkout Button */}
      <div className="mt-4 pt-4 border-t border-gray-600">
        <div className="flex justify-between items-center mb-2">
          <span className="text-lg font-bold text-white">
            Total: ${cartItems.reduce((sum, item) => sum + (item.price * item.quantity), 0).toFixed(2)}
          </span>
        </div>
        <button
          onClick={onCheckout}
          disabled={cartItems.length === 0}
          className="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-3 rounded-lg disabled:opacity-50"
        >
          Checkout
        </button>
      </div>
    </div>
  )
}
