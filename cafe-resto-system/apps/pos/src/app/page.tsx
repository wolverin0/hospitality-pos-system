'use client'

import { useState, useEffect } from 'react'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export default function Home() {
  const [cartOpen, setCartOpen] = useState(false)
  const [cartItems, setCartItems] = useState<any[]>([])
  const [total, setTotal] = useState(0)

  // Register service worker for PWA
  useEffect(() => {
    if ('serviceWorker' in navigator && 'process.env.NODE_ENV' === 'production') {
      navigator.serviceWorker.register('/sw.js')
        .then((registration) => {
          console.log('SW registered: ', registration)
        })
        .catch((error) => {
          console.log('SW registration failed: ', error)
        })
    }
  }, [])

  const addToCart = (item: any) => {
    setCartItems([...cartItems, { ...item, cartId: Date.now() }])
    setTotal(total + item.price)
  }

  const removeFromCart = (cartId: number) => {
    const updatedCart = cartItems.filter((item) => item.cartId !== cartId)
    setCartItems(updatedCart)
    setTotal(total - cartItems.find((item) => item.cartId === cartId)?.price || 0)
  }

  return (
    <div className="flex h-screen overflow-hidden bg-gray-900 text-white">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 px-4 py-3 flex justify-between items-center">
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-bold">POS Terminal</h1>
          <span className="text-sm text-gray-400">v1.0.0</span>
        </div>
        <button
          onClick={() => setCartOpen(!cartOpen)}
          className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg flex items-center gap-2"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h7a3 3 0 00 0 0V3a3 3 0 00 0 0 7 0v-3a3 3 0 00 0-1 1 0 0 0 0 1 1H5v4a1 1 0 00 0-1 1 0 0 0 1.4 0v-4M6 6a1 1 0 00 1 0 0 0 1 .55 0 5.5 5.5 .55 0 5.5 0 0 0 0 1.55 0 .45-1.06-.45 1 1 0 1 0 0 0 1.06" />
          </svg>
          <span>Cart ({cartItems.length})</span>
        </button>
      </header>

      {/* Main Content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Menu Explorer - Left Side */}
        <div className="w-2/3 bg-gray-800 border-r border-gray-700 flex flex-col">
          {/* Category Navigation */}
          <nav className="bg-gray-900 p-4">
            <h2 className="text-lg font-semibold mb-4 text-white">Categories</h2>
            <ul className="space-y-2">
              {['Appetizers', 'Mains', 'Desserts', 'Drinks', 'Specials'].map((category) => (
                <li
                  key={category}
                  className="cursor-pointer hover:bg-gray-700 rounded-lg px-4 py-3 text-gray-200 hover:text-white transition-colors"
                >
                  {category}
                </li>
              ))}
            </ul>
          </nav>

          {/* Menu Items Grid */}
          <div className="flex-1 overflow-y-auto p-4">
            <div className="grid grid-cols-2 gap-4">
              {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map((item) => (
                <div
                  key={item}
                  onClick={() => addToCart({ id: item, name: `Item ${item}`, price: item * 10 })}
                  className="bg-gray-700 hover:bg-gray-600 rounded-lg p-4 cursor-pointer transition-all hover:scale-105 border border-gray-600"
                >
                  <div className="font-semibold">Item {item}</div>
                  <div className="text-green-400 font-bold mt-2">${item * 10}.00}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Cart Panel - Right Side (Slide-over) */}
        <div
          className={`fixed top-0 right-0 h-full w-1/3 bg-gray-800 border-l border-gray-700 flex flex-col transition-transform duration-300 ease-in-out ${
            cartOpen ? 'translate-x-0' : 'translate-x-full'
          }`}
        >
          <div className="p-4 h-full flex flex-col">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-semibold text-white">Cart</h2>
              <button
                onClick={() => setCartOpen(false)}
                className="text-gray-400 hover:text-white"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12M6 6l12-12" />
                </svg>
              </button>
            </div>

            {/* Cart Items */}
            <div className="flex-1 overflow-y-auto space-y-3">
              {cartItems.map((item) => (
                <div
                  key={item.cartId}
                  className="bg-gray-700 rounded-lg p-3 flex justify-between items-center border border-gray-600"
                >
                  <div>
                    <div className="font-medium text-white">{item.name}</div>
                    <div className="text-sm text-gray-400">Qty: {item.quantity || 1}</div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="text-lg font-bold text-green-400">${(item.price * (item.quantity || 1)).toFixed(2)}</div>
                    <button
                      onClick={() => removeFromCart(item.cartId)}
                      className="text-red-400 hover:text-red-300"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 11.67A3 3 0 1 0-0-5.372 11.667-5.373A3 3 0 0 1.004 0 11.667-4.633 0 0 1 1.004 0 11.667-4.633-.734.5-.532A3 3 0 0 0-4.633 1.268-1.268-1.268-3-732-1.732A3 3 0 0 0-2-732.732-.467-1.467-1.467-.467 1.004 0 .004 .004" />
                      </svg>
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {/* Cart Summary */}
            <div className="mt-4 pt-4 border-t border-gray-600">
              <div className="flex justify-between items-center mb-2">
                <span className="text-gray-400">Subtotal</span>
                <span className="text-white font-semibold">${(total * 0.91).toFixed(2)}</span>
              </div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-gray-400">Tax (10%)</span>
                <span className="text-white font-semibold">${(total * 0.09).toFixed(2)}</span>
              </div>
              <div className="flex justify-between items-center mb-4">
                <span className="text-gray-400">Total</span>
                <span className="text-2xl font-bold text-green-400">${total.toFixed(2)}</span>
              </div>

              {/* Action Buttons */}
              <div className="space-y-2">
                <button className="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-3 rounded-lg">
                  Complete Order
                </button>
                <button
                  onClick={() => setCartOpen(false)}
                  className="w-full bg-gray-600 hover:bg-gray-700 text-white font-semibold py-3 rounded-lg"
                >
                  Continue Shopping
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
