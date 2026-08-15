import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import QuizView from '../../views/QuizView.vue'


let session: any
vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { sessionId: 'session' } }),
  useRouter: () => ({ push: vi.fn() }),
}))
vi.mock('../../api', () => ({
  api: vi.fn((path: string) => Promise.resolve(path === '/collections' ? [] : session)),
  jsonBody: (value: unknown) => ({ body: JSON.stringify(value) }),
}))


describe('QuizView', () => {
  beforeEach(() => {
    session = {
      id: 'session', current_index: 0, answers: [], study_states: {},
      config: { study_mode: false, compare_essay: false },
      questions: [],
    }
  })

  it('renders the blank count from answer metadata without receiving answers', async () => {
    session.questions = [{ id: 'fill', type: 'fill', prompt: '两空', case_material: '', explanation: '', source: '', choices: [], answer_meta: { blank_count: 2, unordered: true } }]
    const wrapper = mount(QuizView, { global: { plugins: [ElementPlus] } })
    await flushPromises()
    expect(wrapper.findAll('.fill-list .el-input')).toHaveLength(2)
  })

  it('reveals study-mode answers without submitting', async () => {
    session.config.study_mode = true
    session.questions = [{ id: 'study', type: 'truefalse', prompt: '判断', case_material: '', explanation: '解析内容', source: '', choices: [], answer_spec: { value: true } }]
    const wrapper = mount(QuizView, { global: { plugins: [ElementPlus] } })
    await flushPromises()
    const reveal = wrapper.findAll('button').find(button => button.text().includes('查看答案'))
    expect(reveal).toBeTruthy()
    await reveal!.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('参考答案')
    expect(wrapper.text()).toContain('解析内容')
  })
})
