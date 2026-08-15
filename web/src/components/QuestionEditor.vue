<script setup lang="ts">
import { computed, reactive, watch } from 'vue'
import { Delete, Plus } from '@element-plus/icons-vue'
import type { Question, QuestionType } from '../types'

const props = defineProps<{ modelValue?: Question | null }>()
const emit = defineEmits<{ save: [value: Question]; cancel: [] }>()
const types = [
  { value: 'single', label: '单选题' }, { value: 'multi', label: '多选题' },
  { value: 'any', label: '任意选' }, { value: 'truefalse', label: '判断题' },
  { value: 'fill', label: '填空题' }, { value: 'essay', label: '问答题' },
]
const blank = (): Question => ({ type: 'single', prompt: '', case_material: '', explanation: '', source: '', choices: [
  { label: 'A', content: '', is_correct: true }, { label: 'B', content: '', is_correct: false },
], answer_spec: { correct: ['A'] } })
const form = reactive<Question>(blank())
const fillText = reactive({ value: '' })

watch(() => props.modelValue, (value) => {
  Object.assign(form, value ? JSON.parse(JSON.stringify(value)) : blank())
  if (form.type === 'fill') fillText.value = (form.answer_spec.blanks || []).map((x: string[]) => x.join('/')).join('|')
}, { immediate: true })

const isChoice = computed(() => ['single', 'multi', 'any'].includes(form.type))
function changeType(type: QuestionType) {
  form.type = type
  if (isChoice.value) {
    if (form.choices.length < 2) form.choices = blank().choices
    form.answer_spec = { correct: [form.choices[0]?.label || 'A'] }
  } else if (type === 'truefalse') { form.choices = []; form.answer_spec = { value: true } }
  else if (type === 'fill') { form.choices = []; form.answer_spec = { blanks: [['']], unordered: false } }
  else { form.choices = []; form.answer_spec = { reference: '' } }
}
function toggleCorrect(label: string) {
  const selected: string[] = form.answer_spec.correct || []
  if (form.type === 'single') form.answer_spec.correct = [label]
  else form.answer_spec.correct = selected.includes(label) ? selected.filter(x => x !== label) : [...selected, label]
  form.choices.forEach(c => c.is_correct = form.answer_spec.correct.includes(c.label))
}
function addChoice() {
  const label = String.fromCharCode(65 + form.choices.length)
  form.choices.push({ label, content: '', is_correct: false })
}
function removeChoice(index: number) {
  form.choices.splice(index, 1)
  form.choices.forEach((choice, i) => choice.label = String.fromCharCode(65 + i))
  form.answer_spec.correct = (form.answer_spec.correct || []).filter((x: string) => form.choices.some(c => c.label === x))
}
function submit() {
  if (form.type === 'fill') {
    form.answer_spec.blanks = fillText.value.split('|').map(blank => blank.split('/').map(x => x.trim()).filter(Boolean)).filter(x => x.length)
  }
  emit('save', JSON.parse(JSON.stringify(form)))
}
</script>

<template>
  <el-form label-position="top" class="editor-form" @submit.prevent="submit">
    <el-form-item label="题型">
      <el-segmented :model-value="form.type" :options="types" @change="changeType($event as QuestionType)" />
    </el-form-item>
    <el-form-item label="案例材料（可选）"><el-input v-model="form.case_material" type="textarea" :rows="3" /></el-form-item>
    <el-form-item label="题干" required><el-input v-model="form.prompt" type="textarea" :rows="4" /></el-form-item>

    <template v-if="isChoice">
      <el-form-item label="选项与正确答案">
        <div class="choice-list">
          <div v-for="(choice, index) in form.choices" :key="choice.label" class="choice-row">
            <el-checkbox :model-value="form.answer_spec.correct?.includes(choice.label)" @change="toggleCorrect(choice.label)">{{ choice.label }}</el-checkbox>
            <el-input v-model="choice.content" :placeholder="`选项 ${choice.label}`" />
            <el-tooltip content="删除选项"><el-button :icon="Delete" circle plain @click="removeChoice(index)" /></el-tooltip>
          </div>
          <el-button :icon="Plus" plain :disabled="form.choices.length >= 10" @click="addChoice">添加选项</el-button>
        </div>
      </el-form-item>
    </template>
    <el-form-item v-else-if="form.type === 'truefalse'" label="正确答案">
      <el-segmented v-model="form.answer_spec.value" :options="[{ label: '正确', value: true }, { label: '错误', value: false }]" />
    </el-form-item>
    <template v-else-if="form.type === 'fill'">
      <el-form-item label="可接受答案" required>
        <el-input v-model="fillText.value" placeholder="空与空用 | 分隔，同一空的多个答案用 / 分隔" />
      </el-form-item>
      <el-form-item><el-checkbox v-model="form.answer_spec.unordered">答案无序</el-checkbox></el-form-item>
    </template>
    <el-form-item v-else label="参考答案" required><el-input v-model="form.answer_spec.reference" type="textarea" :rows="5" /></el-form-item>

    <el-form-item label="解析"><el-input v-model="form.explanation" type="textarea" :rows="4" /></el-form-item>
    <el-form-item label="来源"><el-input v-model="form.source" /></el-form-item>
    <div class="form-actions"><el-button @click="emit('cancel')">取消</el-button><el-button type="primary" native-type="submit">保存题目</el-button></div>
  </el-form>
</template>

<style scoped>
.choice-list { width: 100%; display: grid; gap: 10px; }
.choice-row { display: grid; grid-template-columns: 56px 1fr 34px; align-items: center; gap: 8px; }
.form-actions { display: flex; justify-content: flex-end; gap: 10px; padding-top: 16px; border-top: 1px solid var(--qv-border); }
.editor-form :deep(.el-segmented) { max-width: 100%; overflow-x: auto; }
</style>

