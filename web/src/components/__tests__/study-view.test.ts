import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import StudyView from '../../views/StudyView.vue'


const mocks = vi.hoisted(() => ({ api: vi.fn(), loadBanks: vi.fn() }))

vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }))
vi.mock('../../stores/app', () => ({
  useAppStore: () => ({ banks: [{ id: 'bank', name: '题库' }], loadBanks: mocks.loadBanks }),
}))
vi.mock('../../api', () => ({ api: mocks.api }))

describe('StudyView', () => {
  beforeEach(() => {
    mocks.api.mockReset()
    mocks.loadBanks.mockReset().mockResolvedValue(undefined)
    mocks.api.mockImplementation(async (path: string) => {
      if (path === '/stats') return {}
      if (path === '/collections') return []
      if (path.includes('kind=unanswered')) {
        return { items: [{ question: { prompt: '尚未作答的题目' }, wrong_count: 0, mastery: 'new', last_answered_at: null }] }
      }
      if (path.startsWith('/study-states?')) return { items: [] }
      throw new Error(`Unexpected API call: ${path}`)
    })
  })

  it('loads the unanswered question filter from its dedicated tab', async () => {
    const wrapper = mount(StudyView, { global: { plugins: [ElementPlus] } })
    await flushPromises()
    await wrapper.findAll('button').find(button => button.text().includes('未做题'))!.trigger('click')
    await flushPromises()

    expect(mocks.api.mock.calls.some(call => String(call[0]).includes('kind=unanswered'))).toBe(true)
    expect(wrapper.text()).toContain('尚未作答的题目')
  })
})
