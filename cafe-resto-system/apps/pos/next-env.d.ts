/// <reference types="next" />
/// <reference types="next/image-types/global" />

declare global {
  namespace NodeJS {
    interface ProcessEnv {
    NEXT_PUBLIC_API_URL?: string
    NEXT_PUBLIC_WS_URL?: string
  }
  }
}

interface Window {
  workbox: any
}
