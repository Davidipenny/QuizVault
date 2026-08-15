<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Document, Upload } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { api, authorizedDownloadUrl, fileAsBase64, jsonBody } from '../api'
import { useAppStore } from '../stores/app'

const store = useAppStore(), router = useRouter()
const mode = ref('text'), bankId = ref(''), content = ref(''), file = ref<File | null>(null), loading = ref(false)
const job = ref<any>(null)
const sourceType = computed(() => mode.value === 'json' ? 'ai_json' : mode.value)
const sample = `题型：单选题\n1. QuizVault 的本地数据库是什么？\nA. SQLite\nB. Redis\nC. MongoDB\n答案：A\n解析：本地版使用 SQLite。\n---\n题型：填空题\n2. 本应用的名称是____。\n答案：QuizVault`
onMounted(async () => { await store.loadBanks(); bankId.value = store.banks[0]?.id || '' })

async function preview() {
  if (!bankId.value) return ElMessage.warning('请先选择题库')
  loading.value = true
  try {
    let payloadContent = content.value, filename = ''
    if (['excel','word'].includes(mode.value)) {
      if (!file.value) return ElMessage.warning('请选择文件')
      payloadContent = await fileAsBase64(file.value); filename = file.value.name
    }
    job.value = await api('/imports/preview', { method:'POST', ...jsonBody({ bank_id:bankId.value, source_type:sourceType.value, content:payloadContent, filename }) })
  } catch(error:any) { ElMessage.error(error.message) } finally { loading.value=false }
}
async function commit() {
  try {
    job.value = await api(`/imports/${job.value.id}`, { method:'PATCH', ...jsonBody({ rows:job.value.rows }) })
    if (job.value.stats.invalid) return ElMessage.warning('请先修正或排除有问题的题目')
    const result = await api<any>(`/imports/${job.value.id}/commit`, { method:'POST' })
    ElMessage.success(`已导入 ${result.committed} 道题`); job.value=null; await store.loadBanks()
  } catch(error:any) { ElMessage.error(error.message) }
}
function chooseFile(upload:any) { file.value = upload.raw }
function downloadTemplate() { window.open(authorizedDownloadUrl('/imports/template/excel'), '_blank') }
function downloadErrors() { window.open(authorizedDownloadUrl(`/imports/${job.value.id}/errors?download=true`), '_blank') }
</script>

<template>
  <section class="page">
    <header class="page-header"><div><h1>录题中心</h1><p>手工录入、文件导入和 AI JSON</p></div></header>
    <el-tabs v-model="mode" class="import-tabs">
      <el-tab-pane label="手工录题" name="manual">
        <div class="panel panel-body manual"><el-icon size="34"><Document /></el-icon><div><strong>使用六类题型编辑器</strong><p class="muted">选择题库后进入题目管理，可逐题录入和修改。</p></div><el-select v-model="bankId" placeholder="选择题库"><el-option v-for="bank in store.banks" :key="bank.id" :label="bank.name" :value="bank.id" /></el-select><el-button type="primary" :disabled="!bankId" @click="router.push(`/banks/${bankId}/questions`)">进入编辑器</el-button></div>
      </el-tab-pane>
      <el-tab-pane label="文本导入" name="text" />
      <el-tab-pane label="Excel 导入" name="excel" />
      <el-tab-pane label="Word 导入" name="word" />
      <el-tab-pane label="AI JSON" name="json" />
    </el-tabs>

    <template v-if="mode!=='manual'">
      <div class="panel">
        <div class="panel-header"><div class="toolbar"><strong>选择来源</strong><el-button v-if="mode==='excel'" text @click="downloadTemplate">下载标准模板</el-button></div><el-select v-model="bankId" placeholder="目标题库" style="width:220px"><el-option v-for="bank in store.banks" :key="bank.id" :label="bank.name" :value="bank.id" /></el-select></div>
        <div class="panel-body">
          <el-input v-if="['text','json'].includes(mode)" v-model="content" type="textarea" :rows="14" :placeholder="mode==='text'?sample:'粘贴 JSON 题目数组'" />
          <el-upload v-else drag :auto-upload="false" :limit="1" :accept="mode==='excel'?'.xlsx,.xls':'.docx'" :on-change="chooseFile">
            <el-icon class="el-icon--upload"><Upload /></el-icon><div class="el-upload__text">拖入文件或点击选择</div>
          </el-upload>
          <div class="import-actions"><span class="muted">单次最多 3000 题</span><el-button type="primary" :loading="loading" @click="preview">解析并预览</el-button></div>
        </div>
      </div>
      <div v-if="job" class="panel preview">
        <div class="panel-header"><div><strong>导入预览</strong><span class="muted summary">共 {{job.stats.total}} · 可导入 {{job.stats.valid}} · 有问题 {{job.stats.invalid}}</span></div><div class="toolbar"><el-button v-if="job.stats.invalid" @click="downloadErrors">下载错误报告</el-button><el-button type="primary" @click="commit">提交导入</el-button></div></div>
        <el-table :data="job.rows" max-height="460">
          <el-table-column label="导入" width="72"><template #default="{row}"><el-checkbox v-model="row._excluded" :true-value="false" :false-value="true" /></template></el-table-column>
          <el-table-column prop="_row" label="行" width="60" />
          <el-table-column prop="type" label="题型" width="90" />
          <el-table-column label="题干" min-width="320"><template #default="{row}"><el-input v-model="row.prompt" /></template></el-table-column>
          <el-table-column label="校验" min-width="180"><template #default="{row}"><span v-if="row._errors?.length" class="danger-text">{{row._errors.join('；')}}</span><el-tag v-else type="success" effect="plain">通过</el-tag></template></el-table-column>
        </el-table>
      </div>
    </template>

  </section>
</template>

<style scoped>
.import-tabs { margin-bottom:18px }.manual { display:grid; grid-template-columns:auto 1fr minmax(160px,240px) auto; gap:18px; align-items:center }.manual p{margin:5px 0 0}.import-actions{display:flex;align-items:center;justify-content:space-between;margin-top:16px}.preview{margin-top:18px}.summary{margin-left:14px}
@media(max-width:800px){.manual{grid-template-columns:1fr}.summary{display:block;margin:5px 0 0}}
</style>
