<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Download, Refresh, UploadFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { api, authorizedDownloadUrl, fileAsBase64, jsonBody } from '../api'
import { useAppStore } from '../stores/app'

const store=useAppStore(),router=useRouter(),backups=ref<any[]>([]),creating=ref(false)
onMounted(load)
async function load(){backups.value=await api('/backups')}
async function backup(){creating.value=true;try{await api('/backups',{method:'POST'});await load();ElMessage.success('备份已创建')}finally{creating.value=false}}
function download(name:string){window.open(authorizedDownloadUrl(`/backups/${encodeURIComponent(name)}`),'_blank')}
async function restore(upload:any){try{const content=await fileAsBase64(upload.raw);await api('/backups/restore',{method:'POST',...jsonBody({content})});ElMessage.success('数据已恢复，请重新打开应用')}catch(e:any){ElMessage.error(e.message)}}
</script>

<template>
  <section class="page settings-page">
    <header class="page-header"><div><h1>数据与设置</h1><p>外观、备份和本地数据维护</p></div></header>
    <div class="settings-grid">
      <div class="panel panel-body"><h2>外观</h2><div class="setting-row"><div><strong>夜间模式</strong><span>降低暗光环境下的屏幕亮度</span></div><el-switch :model-value="store.dark" @change="store.setDark(Boolean($event))" /></div><div class="setting-row"><div><strong>答题字体</strong><span>{{store.fontSize}} px</span></div><el-slider :model-value="store.fontSize" :min="14" :max="22" :step="1" style="width:180px" @input="store.setFontSize(Number($event))" /></div></div>
      <div class="panel panel-body"><h2>数据迁移与恢复</h2><p class="muted">从旧版 banks 目录迁移，或恢复此前导出的 SQLite 备份。</p><div class="toolbar"><el-button :icon="UploadFilled" @click="router.push('/import')">迁移向导</el-button><el-upload :auto-upload="false" :show-file-list="false" accept=".db" :on-change="restore"><el-button>恢复备份</el-button></el-upload></div></div>
    </div>
    <div class="panel backup-panel">
      <div class="panel-header"><div><strong>本地备份</strong><p class="muted">备份文件保存在 QuizVault 应用数据目录</p></div><div class="toolbar"><el-tooltip content="刷新"><el-button :icon="Refresh" circle @click="load" /></el-tooltip><el-button type="primary" :loading="creating" @click="backup">立即备份</el-button></div></div>
      <el-table :data="backups"><el-table-column prop="filename" label="文件" min-width="280" /><el-table-column label="状态" width="110"><template #default="{row}"><el-tooltip :content="row.validation_error||`数据库版本：${row.revision}`"><el-tag :type="row.valid?'success':'danger'" effect="plain">{{row.valid?'有效':'无效'}}</el-tag></el-tooltip></template></el-table-column><el-table-column label="大小" width="130"><template #default="{row}">{{(row.size/1024).toFixed(1)}} KB</template></el-table-column><el-table-column label="创建时间" width="190"><template #default="{row}">{{new Date(row.created_at).toLocaleString()}}</template></el-table-column><el-table-column label="操作" width="80"><template #default="{row}"><el-tooltip :content="row.valid?'导出备份':'损坏备份不可导出'"><el-button :icon="Download" circle plain :disabled="!row.valid" @click="download(row.filename)" /></el-tooltip></template></el-table-column></el-table>
      <div v-if="!backups.length" class="empty">还没有备份</div>
    </div>
  </section>
</template>

<style scoped>.settings-page{max-width:1100px}.settings-grid{display:grid;grid-template-columns:1.2fr 1fr;gap:18px;margin-bottom:18px}.panel h2{font-size:1rem;margin:0 0 12px}.setting-row{display:flex;align-items:center;justify-content:space-between;gap:24px;padding:15px 0;border-top:1px solid var(--qv-border)}.setting-row span{display:block;color:var(--qv-muted);font-size:.8rem;margin-top:4px}.backup-panel .panel-header p{margin:5px 0 0;font-size:.8rem}@media(max-width:700px){.settings-grid{grid-template-columns:1fr}}
</style>
