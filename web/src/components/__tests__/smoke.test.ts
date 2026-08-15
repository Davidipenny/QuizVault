import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import QuestionEditor from '../QuestionEditor.vue'
import ElementPlus from 'element-plus'

describe('QuestionEditor', () => {
  it('renders all six question types', () => {
    const wrapper = mount(QuestionEditor, { global: { plugins: [ElementPlus] } })
    const text = wrapper.text()
    for (const label of ['单选题', '多选题', '任意选', '判断题', '填空题', '问答题']) {
      expect(text).toContain(label)
    }
  })
})

