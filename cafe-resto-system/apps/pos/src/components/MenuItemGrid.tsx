'use client'

import { useState } from 'react'

interface MenuItem {
  id: string
  name: string
  price: number
  category_id: string
}

interface MenuItemGridProps {
  items: MenuItem[]
  onAddToCart: (item: MenuItem) => void
}

export function MenuItemGrid({ items, onAddToCart }: MenuItemGridProps) {
  return (
    <div className="flex-1 overflow-y-auto p-4">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-4">
        {items.map((item) => (
          <div
            key={item.id}
            onClick={() => onAddToCart(item)}
            className="bg-gray-700 hover:bg-gray-600 rounded-lg p-4 cursor-pointer transition-all hover:scale-105 border border-gray-600"
          >
            <h3 className="text-lg font-semibold text-white">{item.name}</h3>
            <p className="text-2xl font-bold text-green-400">${item.price.toFixed(2)}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
