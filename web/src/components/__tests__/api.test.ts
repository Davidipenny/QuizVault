import { beforeEach, describe, expect, it, vi } from 'vitest'


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
