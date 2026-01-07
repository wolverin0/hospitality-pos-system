import type { NextConfig } from 'next'

const config: NextConfig = {
  reactStrictMode: true,
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**.example.com',
      },
    ],
  },
  webpack: (config) => {
    ...config,
    // Add aliases for absolute imports
    resolve: {
      ...config.resolve,
      alias: {
        '@': './src',
      },
    },
  },
  // PWA Configuration
  async headers() {
    return [
      {
        source: '/manifest.json',
        headers: [
          {
            key: 'Content-Type',
            value: 'application/manifest+json',
          },
        ],
      },
    ]
  },
}

export default config
