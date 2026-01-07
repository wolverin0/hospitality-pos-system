'use client'

import { useState } from 'react'
import { Inter } from 'next/font/google'
import { Clock, CreditCard, ShoppingCart, User, Trash2 as TrashIcon } from 'lucide-react'

interface Category {
  id: string
  name: string
}

interface CategoryNavProps {
  categories: Category[]
  selectedCategory: string | null
  onSelectCategory: (id: string) => void
}

export function CategoryNav({ categories, selectedCategory, onSelectCategory }: CategoryNavProps) {
  return (
    <nav className="w-64 bg-gray-900 p-4 border-r border-gray-700">
      <h2 className="text-sm font-semibold text-white mb-3">Categories</h2>
      <ul className="space-y-1">
        {categories.map((category) => (
          <li
            key={category.id}
            onClick={() => onSelectCategory(category.id)}
            className={\`cursor-pointer rounded-lg px-3 py-2 text-white transition-colors \${
              selectedCategory === category.id
                ? 'bg-blue-600 hover:bg-blue-700'
                : 'bg-gray-800 hover:bg-gray-700'
            }`}
          >
            {category.name}
          </li>
        ))}
      </ul>
    </nav>
  )
}
