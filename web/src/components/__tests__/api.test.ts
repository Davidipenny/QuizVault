import { beforeEach, describe, expect, it, vi } from 'vitest'

const messageError = vi.fn()

vi.mock('element-plus/es/components/message/index.mjs', () => ({
  ElMessage: { error: messageError },
}))


describe('authenticated downloads', () => {
  beforeEach(() => {
    vi.resetModules()
    sessionStorage.clear()
    history.replaceState({}, '', '/?token=desktop-secret')
  })

  it('adds the desktop token to API download URLs', async () => {
    const { authorizedDownloadUrl } = await import('../../api')
    expect(authorizedDownloadUrl('/imports/template/excel')).toBe('/api/v1/imports/template/excel?token=desktop-secret')
    expect(authorizedDownloadUrl('/imports/job/errors?download=true')).toBe('/api/v1/imports/job/errors?download=true&token=desktop-secret')
  })
})

describe('api error surfacing', () => {
  beforeEach(() => {
    vi.resetModules()
    sessionStorage.clear()
    history.replaceState({}, '', '/')
    messageError.mockClear()
    vi.unstubAllGlobals()
  })

  it('toasts the server detail and rejects when the response is not ok', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ detail: '题库名称已存在' }), { status: 409 })))
    const { api } = await import('../../api')

    await expect(api('/banks/1', { method: 'PATCH' })).rejects.toThrow('题库名称已存在')

    await vi.waitFor(() => {
      expect(messageError).toHaveBeenCalledWith({ message: '题库名称已存在', grouping: true })
    })
  })

  it('toasts a connection message when fetch itself fails', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('Failed to fetch') }))
    const { api } = await import('../../api')

    await expect(api('/banks')).rejects.toThrow('无法连接本地服务')

    await vi.waitFor(() => {
      expect(messageError).toHaveBeenCalledWith({ message: '无法连接本地服务，请确认程序仍在运行', grouping: true })
    })
  })
})
