interface TelegramWebApp {
  initData: string
  ready(): void
  isVersionAtLeast?(version: string): boolean
  requestWriteAccess?(callback: (allowed: boolean) => void): void
}

declare global {
  interface Window {
    Telegram?: { WebApp?: TelegramWebApp }
  }
}

export function getTelegramWebApp(): TelegramWebApp | undefined {
  return window.Telegram?.WebApp
}

export function requestTelegramWriteAccess(): Promise<boolean> {
  const app = getTelegramWebApp()
  if (!app?.requestWriteAccess || !app.isVersionAtLeast?.('6.9')) {
    return Promise.resolve(true)
  }
  return new Promise((resolve) => app.requestWriteAccess?.(resolve))
}
