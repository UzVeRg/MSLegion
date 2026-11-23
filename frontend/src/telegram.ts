interface TelegramWebApp {
  initData: string
  ready(): void
  setHeaderColor?(color: string): void
  setBackgroundColor?(color: string): void
  setBottomBarColor?(color: string): void
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

export function syncTelegramColors() {
  const color = getComputedStyle(document.documentElement).getPropertyValue('--background').trim()
  if (!/^#[0-9a-f]{6}$/i.test(color)) return

  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', color)
  const app = getTelegramWebApp()
  if (app?.isVersionAtLeast?.('6.1')) app.setBackgroundColor?.(color)
  if (app?.isVersionAtLeast?.('6.9')) app.setHeaderColor?.(color)
  if (app?.isVersionAtLeast?.('7.10')) app.setBottomBarColor?.(color)
}
