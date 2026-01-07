import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'POS Point of Sale',
  description: 'Hospitality OS Point of Sale for restaurants and cafes',
  manifest: '/manifest.json',
  themeColor: '#1a1a2a',
  viewport: {
    width: 'device-width',
    initialScale: 1,
    maximumScale: 1,
    userScalable: false,
  },
  appleWebApp: {
    capable: true,
    title: 'POS Terminal',
    statusBarStyle: 'black-translucent',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <head>
        <meta charSet="utf-8" />
        <link rel="icon" href="/favicon.ico" />
      </head>
      <body className="bg-gray-50">
        <main className="flex min-h-screen flex-col">
          {children}
        </main>
      </body>
    </html>
  )
}
