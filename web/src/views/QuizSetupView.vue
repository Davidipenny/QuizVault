<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Clock, Reading } from '@element-plus/icons-vue'
import { api, jsonBody } from '../api'
import { useAppStore } from '../stores/app'

const store=useAppStore(), route=useRoute(), router=useRouter(), active=ref<any[]>([]), creating=ref(false)
const form=reactive({bank_id:'',scope:'all',types:['single','multi','any','truefalse','fill','essay'],order:'sequential',shuffle_options:false,study_mode:false,auto_next:false,compare_essay:false,limit:0})
const types=[{label:'单选',value:'single'},{label:'多选',value:'multi'},{label:'任意选',value:'any'},{label:'判断',value:'truefalse'},{label:'填空',value:'fill'},{label:'问答',value:'essay'}]
onMounted(async()=>{await store.loadBanks(); form.bank_id=String(route.query.bank||store.banks[0]?.id||''); active.value=await api('/quiz-sessions/active')})
async function start(){if(!form.bank_id)return ElMessage.warning('请选择题库');creating.value=true;try{const {bank_id,...config}=form;const s=await api<any>('/quiz-sessions',{method:'POST',...jsonBody({bank_id,config})});router.push(`/quiz/${s.id}`)}catch(e:any){ElMessage.error(e.message)}finally{creating.value=false}}
function bankName(id:string){return store.banks.find(b=>b.id===id)?.name||'题库'}
</script>

<template>
  <section class="page setup-page">
    <header class="page-header"><div><h1>刷题设置</h1><p>选择范围、题型和答题行为</p></div></header>
    <div v-if="active.length" class="resume-band"><div><el-icon><Clock /></el-icon><strong>有 {{active.length}} 个未完成会话</strong></div><el-button v-for="item in active.slice(0,2)" :key="item.id" @click="router.push(`/quiz/${item.id}`)">继续 {{bankName(item.bank_id)}} · {{item.current_index}}/{{item.question_order.length}}</el-button></div>
    <div class="setup-grid">
      <div class="panel panel-body">
        <el-form label-position="top">
          <el-form-item label="题库" required><el-select v-model="form.bank_id" filterable style="width:100%"><el-option v-for="bank in store.banks" :key="bank.id" :label="`${bank.name}（${bank.question_count} 题）`" :value="bank.id" /></el-select></el-form-item>
          <el-form-item label="题目范围"><el-segmented v-model="form.scope" :options="[{label:'全部',value:'all'},{label:'错题',value:'wrong'},{label:'收藏',value:'favorite'},{label:'未做',value:'unanswered'}]" /></el-form-item>
          <el-form-item label="题型"><el-checkbox-group v-model="form.types"><el-checkbox v-for="item in types" :key="item.value" :label="item.value" :value="item.value">{{item.label}}</el-checkbox></el-checkbox-group></el-form-item>
          <el-form-item label="题目顺序"><el-segmented v-model="form.order" :options="[{label:'顺序',value:'sequential'},{label:'随机',value:'random'}]" /></el-form-item>
          <el-form-item label="题目数量"><el-input-number v-model="form.limit" :min="0" :max="3000" /><span class="muted form-hint">0 表示全部</span></el-form-item>
        </el-form>
      </div>
      <div class="panel panel-body preferences">
        <strong>答题偏好</strong>
        <div class="setting-row"><div>选项乱序<span>每题随机排列选项</span></div><el-switch v-model="form.shuffle_options" /></div>
        <div class="setting-row"><div>背题模式<span>提交前可直接查看答案</span></div><el-switch v-model="form.study_mode" /></div>
        <div class="setting-row"><div>自动切题<span>答对后自动进入下一题</span></div><el-switch v-model="form.auto_next" /></div>
        <div class="setting-row"><div>问答比对<span>规范化文本后自动比较</span></div><el-switch v-model="form.compare_essay" /></div>
        <el-button type="primary" size="large" :icon="Reading" :loading="creating" @click="start">开始刷题</el-button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.setup-page{max-width:1060px}.resume-band{display:flex;gap:12px;align-items:center;padding:12px 16px;margin-bottom:18px;background:#edf7f5;border:1px solid #b9ded8;border-radius:7px}.dark .resume-band{background:#193431;border-color:#2d5b55}.resume-band>div{display:flex;align-items:center;gap:8px;margin-right:auto}.setup-grid{display:grid;grid-template-columns:1.45fr 1fr;gap:18px}.preferences{display:flex;flex-direction:column;gap:4px}.preferences>strong{margin-bottom:8px}.setting-row{display:flex;justify-content:space-between;align-items:center;padding:16px 0;border-bottom:1px solid var(--qv-border)}.setting-row span{display:block;color:var(--qv-muted);font-size:.78rem;margin-top:3px}.preferences>.el-button{margin-top:auto}.form-hint{margin-left:10px;font-size:.8rem}@media(max-width:800px){.setup-grid{grid-template-columns:1fr}.resume-band{align-items:flex-start;flex-direction:column}.preferences>.el-button{margin-top:20px}}
</style>

