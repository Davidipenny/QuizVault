import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ImportView from '../../views/ImportView.vue'


const mocks = vi.hoisted(() => ({
  api: vi.fn(),
  loadBanks: vi.fn(),
}))

vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }))
vi.mock('../../stores/app', () => ({
  useAppStore: () => ({ banks: [{ id: 'bank', name: '题库' }], loadBanks: mocks.loadBanks }),
}))
vi.mock('../../api', () => ({
  api: mocks.api,
  authorizedDownloadUrl: (path: string) => path,
  fileAsBase64: vi.fn(),
  jsonBody: (value: unknown) => ({ body: JSON.stringify(value) }),
}))

describe('ImportView', () => {
  beforeEach(() => {
    mocks.api.mockReset()
    mocks.loadBanks.mockReset().mockResolvedValue(undefined)
    mocks.api.mockImplementation(async (path: string, options: RequestInit = {}) => {
      if (path === '/imports/preview') {
        return {
          id: 'job', stats: { total: 1, valid: 0, invalid: 1 },
          rows: [{ _row: 1, _excluded: false, _errors: ['题干不能为空'], type: 'single', prompt: '' }],
        }
      }
      if (path === '/imports/job' && options.method === 'PATCH') {
        const rows = JSON.parse(String(options.body)).rows
        return { id: 'job', rows, stats: { total: 1, valid: 1, invalid: 0 } }
      }
      if (path === '/imports/job/commit') return { committed: 0 }
      throw new Error(`Unexpected API call: ${path}`)
    })
  })

  it('submits corrected and excluded preview rows for server-side recalculation', async () => {
    const wrapper = mount(ImportView, { global: { plugins: [ElementPlus] } })
    await flushPromises()
    expect(wrapper.text()).not.toContain('旧版迁移')
    expect(wrapper.text()).not.toContain('扫描旧数据')
    await wrapper.find('textarea').setValue('待解析内容')
    await wrapper.findAll('button').find(button => button.text().includes('解析并预览'))!.trigger('click')
    await flushPromises()

    await wrapper.find('.el-table input[type="text"]').setValue('修正后的题干')
    await wrapper.find('.el-table input[type="checkbox"]').setValue(false)
    await wrapper.findAll('button').find(button => button.text().includes('提交导入'))!.trigger('click')
    await flushPromises()

    const patchCall = mocks.api.mock.calls.find(call => call[0] === '/imports/job')
    const rows = JSON.parse(String(patchCall?.[1]?.body)).rows
    expect(rows[0].prompt).toBe('修正后的题干')
    expect(rows[0]._excluded).toBe(true)
    expect(mocks.api).toHaveBeenCalledWith('/imports/job/commit', { method: 'POST' })
  })
})
