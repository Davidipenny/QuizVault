<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Connection, Delete, Edit, MoreFilled, Plus, Reading } from '@element-plus/icons-vue'
import { api, jsonBody } from '../api'
import { useAppStore } from '../stores/app'
import type { Bank } from '../types'

const store = useAppStore()
const router = useRouter()
const dialog = ref(false)
const editing = ref<Bank | null>(null)
const merging = ref<Bank | null>(null)
const mergeSource = ref('')
const search = ref('')
const form = reactive({ name: '', description: '', tags: [] as string[], challenge_size: 20 })
const filtered = computed(() => store.banks.filter(b => !search.value || `${b.name} ${b.description} ${b.tags.join(' ')}`.toLowerCase().includes(search.value.toLowerCase())))
onMounted(() => store.loadBanks())

function open(bank?: Bank) {
  editing.value = bank || null
  Object.assign(form, bank ? { name: bank.name, description: bank.description, tags: [...bank.tags], challenge_size: bank.challenge_size } : { name: '', description: '', tags: [], challenge_size: 20 })
  dialog.value = true
}
async function save() {
  if (!form.name.trim()) return ElMessage.warning('请输入题库名称')
  if (editing.value) await api(`/banks/${editing.value.id}`, { method: 'PATCH', ...jsonBody(form) })
  else await api('/banks', { method: 'POST', ...jsonBody(form) })
  dialog.value = false; await store.loadBanks(); ElMessage.success('题库已保存')
}
async function remove(bank: Bank) {
  await ElMessageBox.confirm(`删除“${bank.name}”及其全部题目和记录？`, '删除题库', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' })
  await api(`/banks/${bank.id}`, { method: 'DELETE' }); await store.loadBanks()
}
async function merge() {
  if (!merging.value || !mergeSource.value) return
  const result = await api<any>(`/banks/${merging.value.id}/merge`, { method:'POST', ...jsonBody({ source_bank_id:mergeSource.value }) })
  merging.value=null; mergeSource.value=''; await store.loadBanks(); ElMessage.success(`已合并 ${result.copied} 道题，跳过 ${result.skipped} 道重复题`)
}
function formatDate(value?: string) { return value ? new Date(value).toLocaleDateString() : '尚未学习' }
</script>

<template>
  <section class="page">
    <header class="page-header">
      <div><h1>题库中心</h1><p>管理题库、标签和最近学习记录</p></div>
      <el-button type="primary" :icon="Plus" @click="open()">新建题库</el-button>
    </header>
    <div class="stat-strip">
      <div class="stat"><span>题库</span><strong>{{ store.banks.length }}</strong></div>
      <div class="stat"><span>题目总数</span><strong>{{ store.banks.reduce((n,b) => n + b.question_count, 0) }}</strong></div>
      <div class="stat"><span>最近学习</span><strong>{{ store.banks.filter(b => b.last_studied_at).length }}</strong></div>
      <div class="stat"><span>标签</span><strong>{{ new Set(store.banks.flatMap(b => b.tags)).size }}</strong></div>
    </div>
    <div class="panel">
      <div class="panel-header"><el-input v-model="search" clearable placeholder="搜索题库、介绍或标签" style="max-width:360px" /></div>
      <el-table v-if="filtered.length" :data="filtered" v-loading="store.loading" @row-dblclick="(row: Bank) => router.push(`/banks/${row.id}/questions`)">
        <el-table-column label="题库" min-width="260">
          <template #default="{ row }"><div class="bank-name">{{ row.name }}</div><div class="muted bank-desc">{{ row.description || '暂无介绍' }}</div></template>
        </el-table-column>
        <el-table-column prop="question_count" label="题数" width="90" sortable />
        <el-table-column label="标签" min-width="180"><template #default="{ row }"><el-tag v-for="tag in row.tags" :key="tag" size="small" effect="plain">{{ tag }}</el-tag></template></el-table-column>
        <el-table-column label="最近学习" width="130"><template #default="{ row }">{{ formatDate(row.last_studied_at) }}</template></el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-tooltip content="开始刷题"><el-button :icon="Reading" circle plain @click="router.push({ path: '/quiz/setup', query: { bank: row.id } })" /></el-tooltip>
            <el-tooltip content="编辑"><el-button :icon="Edit" circle plain @click="open(row as Bank)" /></el-tooltip>
            <el-tooltip content="合并题库"><el-button :icon="Connection" circle plain @click="merging=row as Bank" /></el-tooltip>
            <el-tooltip content="删除"><el-button :icon="Delete" circle plain type="danger" @click="remove(row as Bank)" /></el-tooltip>
            <el-tooltip content="题目管理"><el-button :icon="MoreFilled" circle plain @click="router.push(`/banks/${row.id}/questions`)" /></el-tooltip>
          </template>
        </el-table-column>
      </el-table>
      <div v-else class="empty">{{ search ? '没有匹配的题库' : '还没有题库，请先新建或迁移旧题库' }}</div>
    </div>
    <el-dialog v-model="dialog" :title="editing ? '编辑题库' : '新建题库'" width="min(520px, 92vw)">
      <el-form label-position="top">
        <el-form-item label="名称" required><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="介绍"><el-input v-model="form.description" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="标签"><el-select v-model="form.tags" multiple filterable allow-create default-first-option style="width:100%" /></el-form-item>
        <el-form-item label="挑战题数"><el-input-number v-model="form.challenge_size" :min="1" :max="1000" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialog=false">取消</el-button><el-button type="primary" @click="save">保存</el-button></template>
    </el-dialog>
    <el-dialog :model-value="!!merging" title="合并题库" width="min(460px,92vw)" @close="merging=null">
      <p>将其他题库复制到“{{merging?.name}}”，重复题目会自动跳过。</p>
      <el-select v-model="mergeSource" placeholder="选择来源题库" style="width:100%"><el-option v-for="item in store.banks.filter(x=>x.id!==merging?.id)" :key="item.id" :label="`${item.name}（${item.question_count} 题）`" :value="item.id" /></el-select>
      <template #footer><el-button @click="merging=null">取消</el-button><el-button type="primary" :disabled="!mergeSource" @click="merge">开始合并</el-button></template>
    </el-dialog>
  </section>
</template>

<style scoped>
.bank-name { font-weight: 650; margin-bottom: 4px; }.bank-desc { font-size: .82rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }.el-tag + .el-tag { margin-left: 5px; }
</style>
