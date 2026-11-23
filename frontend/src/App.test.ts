import { setImmediate } from 'node:timers/promises'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createApp } from 'vue'
import App from './App.vue'

const profile = {
  id: 'c43f518f-c3fd-45f0-8a90-b8bad20dbf65',
  telegram_id: 42,
  display_name: 'Анна Иванова',
  telegram_notifications_enabled: false,
}
const cleanup: Array<() => void> = []

function loginResponse(duration = 60_000) {
  return Response.json({
    access_token: 'test-session',
    token_type: 'bearer',
    expires_at: new Date(Date.now() + duration).toISOString(),
  })
}

function pendingResponse() {
  let resolveResponse!: (response: Response) => void
  const promise = new Promise<Response>((resolve) => { resolveResponse = resolve })
  return { promise, resolve: resolveResponse }
}

function mount() {
  const host = document.createElement('div')
  document.body.append(host)
  const app = createApp(App)
  app.mount(host)
  cleanup.push(() => {
    app.unmount()
    host.remove()
  })
  return host
}

function openMiniApp(requestWriteAccess?: (callback: (allowed: boolean) => void) => void) {
  const ready = vi.fn()
  vi.stubGlobal('Telegram', {
    WebApp: {
      initData: 'auth_date=1&hash=signed', ready, requestWriteAccess, isVersionAtLeast: () => true,
    },
  })
  return { host: mount(), ready }
}

function clickAction(host: HTMLElement) {
  const button = host.querySelector('button')
  if (!button) throw new Error('Кнопка действия отсутствует')
  button.click()
}

afterEach(() => {
  for (const unmount of cleanup.splice(0)) unmount()
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

describe('Оформление Mini App', () => {
  afterEach(() => {
    localStorage.removeItem('mslegion.theme')
    delete document.documentElement.dataset.theme
  })

  it('использует чёрный графит при неизвестной сохранённой теме', () => {
    localStorage.setItem('mslegion.theme', 'unknown')
    const settings = mount().querySelector('details')
    expect(settings?.querySelector('summary')?.textContent).toBe('Настройки')
    expect(settings?.querySelector('select')?.value).toBe('graphite')
    expect(document.documentElement.dataset.theme).toBe('graphite')
  })

  it('применяет каждую тему и восстанавливает последнюю при открытии', async () => {
    const select = mount().querySelector('select')
    expect(select).not.toBeNull()
    for (const theme of ['neo-gothic', 'network', 'underground', 'graphite', 'network']) {
      select!.value = theme
      select!.dispatchEvent(new Event('change'))
      await setImmediate()
      expect(document.documentElement.dataset.theme).toBe(theme)
    }

    expect(mount().querySelector('select')?.value).toBe('network')
  })
})

describe('Telegram Mini App', () => {
  it('просит разрешение Telegram перед включением уведомлений', async () => {
    const permission = vi.fn((callback: (allowed: boolean) => void) => callback(true))
    const request = vi.fn()
      .mockResolvedValueOnce(loginResponse())
      .mockResolvedValueOnce(Response.json(profile))
      .mockResolvedValueOnce(Response.json({ enabled: true }))
      .mockResolvedValueOnce(Response.json({ enabled: false }))
    vi.stubGlobal('fetch', request)
    const { host } = openMiniApp(permission)
    await setImmediate()
    const button = host.querySelector<HTMLButtonElement>('[data-notification-toggle]')!
    button.click()
    await setImmediate()
    expect(permission).toHaveBeenCalledOnce()
    expect(request).toHaveBeenLastCalledWith(
      '/api/v1/auth/me/telegram-notifications',
      expect.objectContaining({ method: 'PUT', body: JSON.stringify({ enabled: true }) }),
    )
    expect(button.textContent).toContain('Отключить уведомления')
    button.click()
    await setImmediate()
    expect(permission).toHaveBeenCalledOnce()
    expect(button.textContent).toContain('Включить уведомления')
  })

  it('показывает подсказку вне Telegram без запроса к API', async () => {
    const request = vi.fn()
    vi.stubGlobal('fetch', request)
    const host = mount()
    await setImmediate()
    expect(host.textContent).toContain('Откройте MSLegion в Telegram')
    expect(request).not.toHaveBeenCalled()
  })

  it('показывает загрузку и запрашивает профиль с серверной сессией', async () => {
    const login = pendingResponse()
    const request = vi.fn()
      .mockReturnValueOnce(login.promise)
      .mockResolvedValueOnce(Response.json(profile))
    vi.stubGlobal('fetch', request)
    const { host, ready } = openMiniApp()
    await setImmediate()
    expect(host.textContent).toContain('Входим через Telegram')
    login.resolve(loginResponse())
    await setImmediate()
    expect(ready).toHaveBeenCalledOnce()
    expect(request).toHaveBeenNthCalledWith(1, '/api/v1/auth/telegram', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({ init_data: 'auth_date=1&hash=signed' }),
    }))
    expect(request).toHaveBeenNthCalledWith(2, '/api/v1/auth/me', expect.objectContaining({
      headers: { Authorization: 'Bearer test-session' },
    }))
    expect(host.textContent).toContain('Анна Иванова')
    expect(localStorage.length).toBe(0)
    expect(sessionStorage.length).toBe(0)
  })

  it('убирает профиль по истечении срока и позволяет войти снова', async () => {
    vi.useFakeTimers({ toFake: ['Date', 'setTimeout', 'clearTimeout'] })
    const request = vi.fn()
      .mockResolvedValueOnce(loginResponse(1_000))
      .mockResolvedValueOnce(Response.json(profile))
      .mockResolvedValueOnce(loginResponse())
      .mockResolvedValueOnce(Response.json(profile))
    vi.stubGlobal('fetch', request)
    const { host } = openMiniApp()
    await setImmediate()
    await vi.advanceTimersByTimeAsync(1_000)
    expect(host.textContent).toContain('Сессия завершилась')
    expect(host.textContent).not.toContain('Анна Иванова')
    clickAction(host)
    await setImmediate()
    expect(host.textContent).toContain('Анна Иванова')
  })

  it('просит открыть приложение заново, если данные Telegram устарели', async () => {
    const request = vi.fn().mockResolvedValueOnce(Response.json({}, { status: 401 }))
    vi.stubGlobal('fetch', request)
    const { host } = openMiniApp()
    await setImmediate()
    expect(host.textContent).toContain('Откройте приложение заново в Telegram')
    expect(request).toHaveBeenCalledOnce()
  })

  it('при сетевой ошибке повторяет запрос профиля с уже выданной сессией', async () => {
    const request = vi.fn()
      .mockResolvedValueOnce(loginResponse())
      .mockRejectedValueOnce(new TypeError('Сеть недоступна'))
      .mockResolvedValueOnce(Response.json(profile))
    vi.stubGlobal('fetch', request)
    const { host } = openMiniApp()
    await setImmediate()
    expect(host.textContent).toContain('Не удалось загрузить профиль')
    clickAction(host)
    await setImmediate()
    expect(request.mock.calls.map(([path]) => path)).toEqual([
      '/api/v1/auth/telegram', '/api/v1/auth/me', '/api/v1/auth/me',
    ])
    expect(host.textContent).toContain('Анна Иванова')
  })

  it('отзывает текущую сессию при выходе', async () => {
    const request = vi.fn()
      .mockResolvedValueOnce(loginResponse())
      .mockResolvedValueOnce(Response.json(profile))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
    vi.stubGlobal('fetch', request)
    const { host } = openMiniApp()
    await setImmediate()
    clickAction(host)
    await setImmediate()
    expect(request).toHaveBeenLastCalledWith('/api/v1/auth/logout', expect.objectContaining({
      method: 'POST',
      headers: { Authorization: 'Bearer test-session' },
    }))
    expect(host.textContent).toContain('Вы вышли из профиля')
    expect(host.textContent).not.toContain('Анна Иванова')
  })

  it('поздний ответ выхода не сбрасывает новую сессию', async () => {
    vi.useFakeTimers({ toFake: ['Date', 'setTimeout', 'clearTimeout'] })
    const pendingLogout = pendingResponse()
    const request = vi.fn()
      .mockResolvedValueOnce(loginResponse(1_000))
      .mockResolvedValueOnce(Response.json(profile))
      .mockReturnValueOnce(pendingLogout.promise)
      .mockResolvedValueOnce(loginResponse())
      .mockResolvedValueOnce(Response.json(profile))
    vi.stubGlobal('fetch', request)
    const { host } = openMiniApp()
    await setImmediate()
    clickAction(host)
    await vi.advanceTimersByTimeAsync(1_000)
    clickAction(host)
    await setImmediate()
    pendingLogout.resolve(new Response(null, { status: 204 }))
    await setImmediate()
    expect(host.textContent).toContain('Анна Иванова')
  })
})
