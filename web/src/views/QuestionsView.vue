<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Back, CopyDocument, Delete, Edit, Plus, Rank } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import QuestionEditor from '../components/QuestionEditor.vue'
import { api, jsonBody } from '../api'
import { useAppStore } from '../stores/app'
import type { EditableQuestion } from '../types'

const route = useRoute(), router = useRouter(), store = useAppStore()
const bankId = computed(() => String(route.params.bankId))
const bank = computed(() => store.banks.find(b => b.id === bankId.value))
const loading = ref(false), items = ref<EditableQuestion[]>([]), total = ref(0), selected = ref<EditableQuestion[]>([])
const drawer = ref(false), editing = ref<EditableQuestion | null>(null), batchDialog = ref(false)
const query = reactive({ search: '', type: '', page: 1, page_size: 30 })
const batch = reactive({ action: 'copy', target_bank_id: '' })
const typeLabels: Record<string,string> = { single:'单选', multi:'多选', any:'任意选', truefalse:'判断', fill:'填空', essay:'问答' }

onMounted(async () => { if (!store.banks.length) await store.loadBanks(); await load() })
watch(() => [query.type, query.page], load)
let timer: number
watch(() => query.search, () => { clearTimeout(timer); timer = window.setTimeout(() => { query.page=1; load() }, 250) })
async function load() {
  loading.value = true
  try {
    const params = new URLSearchParams({ page:String(query.page), page_size:String(query.page_size), search:query.search, question_type:query.type })
    const data = await api<any>(`/banks/${bankId.value}/questions?${params}`); items.value=data.items; total.value=data.total
  } finally { loading.value=false }
}
function open(question?: EditableQuestion) { editing.value = question || null; drawer.value=true }
async function save(value: EditableQuestion) {
  try {
    if (editing.value?.id) await api(`/questions/${editing.value.id}`, { method:'PUT', ...jsonBody(value) })
    else await api(`/banks/${bankId.value}/questions`, { method:'POST', ...jsonBody(value) })
    drawer.value=false; await load(); await store.loadBanks(); ElMessage.success('题目已保存')
  } catch (error:any) { ElMessage.error(error.message) }
}
async function remove(question: EditableQuestion) {
  await ElMessageBox.confirm('确认删除这道题？', '删除题目', { type:'warning' }); await api(`/questions/${question.id}`, { method:'DELETE' }); await load()
}
async function runBatch() {
  if (!selected.value.length) return
  if (batch.action !== 'delete' && !batch.target_bank_id) return ElMessage.warning('请选择目标题库')
  await api('/questions/batch', { method:'POST', ...jsonBody({ action:batch.action, target_bank_id:batch.target_bank_id, question_ids:selected.value.map(x=>x.id) }) })
  batchDialog.value=false; selected.value=[]; await load(); await store.loadBanks(); ElMessage.success('批量操作完成')
}
</script>

<template>
  <section class="page">
    <header class="page-header">
      <div><el-button text :icon="Back" @click="router.push('/banks')">返回题库</el-button><h1>{{ bank?.name || '题目管理' }}</h1><p>搜索、编辑和批量整理题目</p></div>
      <el-button type="primary" :icon="Plus" @click="open()">手工录题</el-button>
    </header>
    <div class="panel">
      <div class="panel-header toolbar">
        <el-input v-model="query.search" clearable placeholder="搜索题干、解析或来源" style="width:min(360px,100%)" />
        <el-select v-model="query.type" clearable placeholder="全部题型" style="width:140px"><el-option v-for="(label,key) in typeLabels" :key="key" :label="label" :value="key" /></el-select>
        <el-button :icon="Rank" :disabled="!selected.length" @click="batchDialog=true">批量操作 ({{ selected.length }})</el-button>
      </div>
      <el-table :data="items" v-loading="loading" @selection-change="selected=$event">
        <el-table-column type="selection" width="46" />
        <el-table-column label="题型" width="82"><template #default="{row}"><el-tag class="type-tag" effect="plain">{{ typeLabels[row.type] }}</el-tag></template></el-table-column>
        <el-table-column label="题干" min-width="360" show-overflow-tooltip><template #default="{row}">{{ row.prompt }}</template></el-table-column>
        <el-table-column prop="source" label="来源" width="150" show-overflow-tooltip />
        <el-table-column label="操作" width="104" fixed="right"><template #default="{row}">
          <el-tooltip content="编辑"><el-button :icon="Edit" circle plain @click="open(row)" /></el-tooltip>
          <el-tooltip content="删除"><el-button :icon="Delete" circle plain type="danger" @click="remove(row)" /></el-tooltip>
        </template></el-table-column>
      </el-table>
      <div class="pager"><el-pagination v-model:current-page="query.page" :page-size="query.page_size" :total="total" layout="total, prev, pager, next" /></div>
    </div>
    <el-drawer v-model="drawer" :title="editing ? '编辑题目' : '新增题目'" size="min(680px, 96vw)" destroy-on-close><QuestionEditor :model-value="editing" @save="save" @cancel="drawer=false" /></el-drawer>
    <el-dialog v-model="batchDialog" title="批量操作" width="min(440px,92vw)">
      <el-form label-position="top"><el-form-item label="操作"><el-segmented v-model="batch.action" :options="[{label:'复制',value:'copy'},{label:'移动',value:'move'},{label:'删除',value:'delete'}]" /></el-form-item>
      <el-form-item v-if="batch.action!=='delete'" label="目标题库"><el-select v-model="batch.target_bank_id" style="width:100%"><el-option v-for="item in store.banks.filter(x=>x.id!==bankId)" :key="item.id" :label="item.name" :value="item.id" /></el-select></el-form-item></el-form>
      <template #footer><el-button @click="batchDialog=false">取消</el-button><el-button :type="batch.action==='delete'?'danger':'primary'" :icon="batch.action==='copy'?CopyDocument:Delete" @click="runBatch">执行</el-button></template>
    </el-dialog>
  </section>
</template>

<style scoped>.page-header h1 { margin-top:8px }.pager { display:flex; justify-content:flex-end; padding:16px 18px; border-top:1px solid var(--qv-border); }</style>
