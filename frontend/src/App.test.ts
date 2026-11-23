import { setImmediate } from 'node:timers/promises'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createApp, nextTick } from 'vue'
import App from './App.vue'

const profile = {
  id: 'c43f518f-c3fd-45f0-8a90-b8bad20dbf65',
  telegram_id: 42,
  display_name: 'Анна Иванова',
  telegram_notifications_enabled: false,
}
const emptyWallet = {
  balance: '0', date: '2026-11-23', streak: 0, day: 1, claimed_today: false,
  seconds_until_reset: 3600, rewards: [{ day: 1, amount: 10 }, { day: 2, amount: 20 }],
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
  const button = host.querySelector<HTMLButtonElement>('main .primary, main .secondary')
  if (!button) throw new Error('Кнопка действия отсутствует')
  button.click()
}

async function clickLabel(host: HTMLElement, label: string) {
  const element = Array.from(host.querySelectorAll<HTMLElement>('button, a')).find((item) =>
    item.getAttribute('aria-label') === label || item.textContent?.trim() === label,
  )
  if (!element) throw new Error(`Не найден элемент «${label}»`)
  element.click()
  await nextTick()
}

async function openPage(host: HTMLElement, label: string) {
  await clickLabel(host, 'Меню')
  await clickLabel(host, label)
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

  it('использует чёрный графит при неизвестной сохранённой теме', async () => {
    localStorage.setItem('mslegion.theme', 'unknown')
    const host = mount()
    await openPage(host, 'Настройки')
    expect(host.querySelector<HTMLSelectElement>('#theme-select')?.value).toBe('graphite')
    expect(document.documentElement.dataset.theme).toBe('graphite')
  })

  it('применяет каждую тему и восстанавливает последнюю при открытии', async () => {
    const host = mount()
    await openPage(host, 'Настройки')
    const select = host.querySelector<HTMLSelectElement>('#theme-select')
    expect(select).not.toBeNull()
    for (const theme of ['neo-gothic', 'network', 'underground', 'graphite', 'network']) {
      select!.value = theme
      select!.dispatchEvent(new Event('change'))
      await setImmediate()
      expect(document.documentElement.dataset.theme).toBe(theme)
    }

    const reopened = mount()
    await openPage(reopened, 'Настройки')
    expect(reopened.querySelector<HTMLSelectElement>('#theme-select')?.value).toBe('network')
  })
})

describe('FAQ', () => {
  it.each(['graphite', 'neo-gothic', 'network', 'underground'])(
    'открывает публичный FAQ, ответы и контакты в теме %s', async (theme) => {
      localStorage.setItem('mslegion.theme', theme)
      cleanup.push(() => localStorage.removeItem('mslegion.theme'))
      const fetch = vi.fn(async () => Response.json({
        questions: [{ question: 'Как получить LC?', answer: 'Ежедневно отмечайтесь в профиле.' }],
        contacts: [{ channel: 'telegram', label: '@MsLegionSupport_bot', url: 'https://t.me/MsLegionSupport_bot' }],
      }))
      vi.stubGlobal('fetch', fetch)
      const host = mount()
      await clickLabel(host, 'Меню')
      const items = Array.from(host.querySelectorAll('.nav-row')).map((row) => row.textContent?.trim())
      const index = items.indexOf('FAQ')
      expect(items.slice(index - 1, index + 2)).toEqual(['Уведомления', 'FAQ', 'Настройки'])
      await clickLabel(host, 'FAQ')
      await setImmediate()
      expect(document.documentElement.dataset.theme).toBe(theme)
      expect(fetch).toHaveBeenCalledWith('/api/v1/support?language=ru', expect.anything())
      expect(Array.from(host.querySelectorAll('main h2')).map((item) => item.textContent)).toEqual([
        'Частые вопросы', 'Связь с администрацией',
      ])
      const question = Array.from(host.querySelectorAll('main summary')).find((item) =>
        item.textContent?.trim() === 'Как получить LC?',
      )
      expect(question?.parentElement?.textContent).toContain('Ежедневно отмечайтесь в профиле.')
      expect(host.querySelector('main a')?.getAttribute('href')).toBe('https://t.me/MsLegionSupport_bot')
    },
  )
})

describe('Навигация Mini App', () => {
  afterEach(() => {
    localStorage.removeItem('mslegion.language')
    document.documentElement.lang = 'ru'
  })

  it('открывает главную и переходит в раздел из меню', async () => {
    const host = mount()
    expect(host.querySelector('h1')?.textContent).toBe('Главная')
    await clickLabel(host, 'Меню')
    const menu = host.querySelector('nav')
    expect(menu?.textContent).toContain('Профиль')
    for (const label of ['Игры', 'События', 'Медиа', 'Сообщества', 'Уведомления', 'Настройки']) {
      expect(menu?.textContent).toContain(label)
    }
    await clickLabel(host, 'События')
    expect(host.querySelector('h1')?.textContent).toBe('События')
    await clickLabel(host, 'MSLegion')
    expect(host.querySelector('h1')?.textContent).toBe('Главная')
  })

  it.each(['graphite', 'neo-gothic', 'network', 'underground'])(
    'открывает «Мафию» из игр в теме %s', async (theme) => {
      localStorage.setItem('mslegion.theme', theme)
      try {
        const host = mount()
        await openPage(host, 'Игры')
        await clickLabel(host, 'Мафия')
        expect(host.querySelector('h1')?.textContent).toBe('Мафия')
        expect(document.documentElement.dataset.theme).toBe(theme)
        expect(host.textContent).toContain('Откройте MSLegion в Telegram')
      } finally {
        localStorage.removeItem('mslegion.theme')
      }
    },
  )

  it('создаёт настраиваемую комнату и показывает участнику его роль', async () => {
    const settings = {
      mode: 'custom', doctor: false, detective: true, night_seconds: 45,
      day_seconds: 90, vote_seconds: 35,
    }
    const room = {
      code: 'AB12CD34EF', settings, host_id: profile.id, phase: 'night',
      round: 1, turn: 1, deadline: new Date(Date.now() + 45_000).toISOString(),
      server_time: new Date().toISOString(), winner: null,
      players: [{ id: profile.id, name: profile.display_name, alive: true, role: null }],
      role: 'detective', allies: [], eligible_targets: [], can_target: true, target_locked: false,
      target_id: null, vote_count: null, history: [], investigations: [], messages: [],
      chat: null, can_chat: false,
    }
    const fetch = vi.fn((url: string, options: RequestInit = {}) => {
      if (url.endsWith('/auth/telegram')) return Promise.resolve(loginResponse())
      if (url.endsWith('/auth/me')) return Promise.resolve(Response.json(profile))
      if (url.endsWith('/mafia/rooms') && options.method === 'POST') {
        expect(JSON.parse(String(options.body))).toEqual(settings)
        return Promise.resolve(Response.json(room))
      }
      return Promise.resolve(Response.json([]))
    })
    vi.stubGlobal('fetch', fetch)
    const { host } = openMiniApp()
    await openPage(host, 'Игры')
    await clickLabel(host, 'Мафия')
    await setImmediate()
    const mode = host.querySelector<HTMLSelectElement>('#mafia-mode')!
    mode.value = 'custom'
    mode.dispatchEvent(new Event('change'))
    await nextTick()
    const doctor = host.querySelector<HTMLInputElement>('#mafia-doctor')!
    doctor.checked = false
    doctor.dispatchEvent(new Event('change'))
    await clickLabel(host, 'Создать комнату')
    await setImmediate()
    expect(host.textContent).toContain('Ваша роль')
    expect(host.textContent).toContain('Комиссар')
    expect(host.textContent).toContain('Ночь')
    expect(host.textContent).toContain('AB12CD34EF')
  })

  it('делает акцент на событиях с главной и отмечает открытый раздел', async () => {
    const host = mount()
    await clickLabel(host, 'Меню')
    expect(host.querySelector('.nav-row--featured')?.textContent?.trim()).toBe('События')
    expect(host.querySelector('nav [aria-current]')).toBeNull()

    await clickLabel(host, 'Игры')
    await clickLabel(host, 'Меню')
    expect(host.querySelector('.nav-row--featured')).toBeNull()
    expect(host.querySelector('nav [aria-current="page"]')?.textContent?.trim()).toBe('Игры')
  })

  it('фильтрует разделы и открывает результат поиска', async () => {
    const host = mount()
    await clickLabel(host, 'Поиск')
    const input = host.querySelector<HTMLInputElement>('input[type="search"]')!
    input.value = '  СОБЫ '
    input.dispatchEvent(new Event('input'))
    await nextTick()
    expect(host.querySelector('main')?.textContent).toContain('События')
    expect(host.querySelector('main')?.textContent).not.toContain('Игры')
    await clickLabel(host, 'События')
    expect(host.querySelector('h1')?.textContent).toBe('События')
  })

  it('переводит интерфейс и сохраняет язык при повторном запуске', async () => {
    const host = mount()
    const select = host.querySelector<HTMLSelectElement>('#language-select')!
    select.value = 'en'
    select.dispatchEvent(new Event('change'))
    await nextTick()
    expect(document.documentElement.lang).toBe('en')
    expect(host.querySelector('h1')?.textContent).toBe('Home')
    expect(mount().querySelector('h1')?.textContent).toBe('Home')
    await clickLabel(host, 'Menu')
    expect(host.querySelector('nav')?.textContent).toContain('Communities')
  })

  it('загружает сообщества пользователя при открытии вкладки', async () => {
    const request = vi.fn()
      .mockResolvedValueOnce(loginResponse())
      .mockResolvedValueOnce(Response.json(profile))
      .mockResolvedValueOnce(Response.json([{ id: 'community-1', name: 'Клуб', owner_id: profile.id }]))
    vi.stubGlobal('fetch', request)
    const { host } = openMiniApp()
    await setImmediate()
    await openPage(host, 'Сообщества')
    await setImmediate()
    expect(request).toHaveBeenLastCalledWith(
      '/api/v1/communities?offset=0&limit=50',
      expect.objectContaining({ headers: { Authorization: 'Bearer test-session' } }),
    )
    expect(host.querySelector('main')?.textContent).toContain('Клуб')
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
    await openPage(host, 'Уведомления')
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
    await openPage(host, 'Профиль')
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
    await openPage(host, 'Профиль')
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
      .mockResolvedValueOnce(Response.json(emptyWallet))
      .mockResolvedValueOnce(loginResponse())
      .mockResolvedValueOnce(Response.json(profile))
    vi.stubGlobal('fetch', request)
    const { host } = openMiniApp()
    await openPage(host, 'Профиль')
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
    await openPage(host, 'Профиль')
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
    await openPage(host, 'Профиль')
    await setImmediate()
    expect(host.textContent).toContain('Не удалось загрузить профиль')
    clickAction(host)
    await setImmediate()
    expect(request.mock.calls.map(([path]) => path)).toEqual([
      '/api/v1/auth/telegram', '/api/v1/auth/me', '/api/v1/auth/me', '/api/v1/finance/wallet',
    ])
    expect(host.textContent).toContain('Анна Иванова')
  })

  it('отзывает текущую сессию при выходе', async () => {
    const request = vi.fn()
      .mockResolvedValueOnce(loginResponse())
      .mockResolvedValueOnce(Response.json(profile))
      .mockResolvedValueOnce(Response.json(emptyWallet))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
    vi.stubGlobal('fetch', request)
    const { host } = openMiniApp()
    await openPage(host, 'Профиль')
    await setImmediate()
    await clickLabel(host, 'Выйти')
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
      .mockResolvedValueOnce(Response.json(emptyWallet))
      .mockReturnValueOnce(pendingLogout.promise)
      .mockResolvedValueOnce(loginResponse())
      .mockResolvedValueOnce(Response.json(profile))
    vi.stubGlobal('fetch', request)
    const { host } = openMiniApp()
    await openPage(host, 'Профиль')
    await setImmediate()
    await clickLabel(host, 'Выйти')
    await vi.advanceTimersByTimeAsync(1_000)
    clickAction(host)
    await setImmediate()
    pendingLogout.resolve(new Response(null, { status: 204 }))
    await setImmediate()
    expect(host.textContent).toContain('Анна Иванова')
  })
})

describe('Баланс LC в профиле', () => {
  it('после смены даты обновляет состояние и ждёт нового нажатия', async () => {
    const nextDay = { ...emptyWallet, date: '2026-11-24', streak: 1, day: 2, balance: '10' }
    const request = vi.fn()
      .mockResolvedValueOnce(loginResponse())
      .mockResolvedValueOnce(Response.json(profile))
      .mockResolvedValueOnce(Response.json(emptyWallet))
      .mockResolvedValueOnce(new Response(null, { status: 409 }))
      .mockResolvedValueOnce(Response.json(nextDay))
    vi.stubGlobal('fetch', request)

    const { host } = openMiniApp()
    await openPage(host, 'Профиль')
    await setImmediate()
    await clickLabel(host, 'Отметиться · +10 LC')
    await setImmediate()

    expect(host.querySelector('.lc-claim')?.textContent).toContain('Отметиться · +20 LC')
    expect(request.mock.calls.filter(([url]) => url.endsWith('/check-in'))).toHaveLength(1)
    expect(request).toHaveBeenLastCalledWith('/api/v1/finance/wallet', expect.anything())
  })

  it.each(['graphite', 'neo-gothic', 'network', 'underground'])(
    'показывает баланс, серию и выдаёт отметку в теме %s', async (theme) => {
      localStorage.setItem('mslegion.theme', theme)
      try {
        const wallet = emptyWallet
        const fetch = vi.fn((url: string, options: RequestInit = {}) => {
          if (url.endsWith('/auth/telegram')) return Promise.resolve(loginResponse())
          if (url.endsWith('/auth/me')) return Promise.resolve(Response.json(profile))
          if (url.endsWith('/finance/wallet')) return Promise.resolve(Response.json(wallet))
          if (url.endsWith('/finance/wallet/check-in')) {
            expect(options.method).toBe('POST')
            expect(JSON.parse(String(options.body))).toEqual({ date: wallet.date })
            return Promise.resolve(Response.json({ ...wallet, balance: '10', streak: 1, claimed_today: true }))
          }
          return Promise.resolve(new Response(null, { status: 404 }))
        })
        vi.stubGlobal('fetch', fetch)
        const { host } = openMiniApp()
        await openPage(host, 'Профиль')
        await setImmediate()
        expect(document.documentElement.dataset.theme).toBe(theme)
        expect(host.querySelector('.lc-amount')?.textContent).toBe('0')
        expect(host.querySelector('.lc-balance img')).not.toBeNull()
        expect(host.textContent).toContain('Серия входов: 0')
        expect(host.textContent).toContain('День 2')
        await clickLabel(host, 'Отметиться · +10 LC')
        await setImmediate()
        expect(host.querySelector('.lc-amount')?.textContent).toBe('10')
        expect(host.textContent).toContain('Серия входов: 1')
        expect(host.textContent).toContain('Сегодня отмечено')
        expect(fetch.mock.calls.filter(([url]) => url.endsWith('/check-in'))).toHaveLength(1)
      } finally {
        localStorage.removeItem('mslegion.theme')
      }
    },
  )
})
