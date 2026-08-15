<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Reading } from '@element-plus/icons-vue'
import { api } from '../api'
import { useAppStore } from '../stores/app'
const router=useRouter(),store=useAppStore(),tab=ref('wrong'),bankId=ref(''),collectionId=ref(''),collections=ref<any[]>([]),items=ref<any[]>([]),stats=ref<any>({}),loading=ref(false)
const tabs=[{label:'错题',value:'wrong'},{label:'快速收藏',value:'favorite'},{label:'收藏夹',value:'collection'},{label:'笔记',value:'note'},{label:'纠错标记',value:'flagged'},{label:'答题历史',value:'history'}]
onMounted(async()=>{await store.loadBanks();[stats.value,collections.value]=await Promise.all([api('/stats'),api('/collections')]);collectionId.value=collections.value[0]?.id||'';load()});watch([tab,bankId,collectionId],load)
async function load(){loading.value=true;try{if(tab.value==='history'){const p=new URLSearchParams({bank_id:bankId.value});items.value=(await api<any>(`/quiz-answers?${p}`)).items}else if(tab.value==='collection'){if(!collectionId.value){items.value=[];return}const data=await api<any>(`/collections/${collectionId.value}/questions`);items.value=data.items.map((question:any)=>({question,collection:true}))}else{const p=new URLSearchParams({kind:tab.value,bank_id:bankId.value});items.value=(await api<any>(`/study-states?${p}`)).items}}finally{loading.value=false}}
</script>

<template>
  <section class="page">
    <header class="page-header"><div><h1>学习记录</h1><p>集中查看错题、收藏、笔记和掌握情况</p></div><el-button type="primary" :icon="Reading" @click="router.push('/quiz/setup')">重新练习</el-button></header>
    <div class="stat-strip"><div class="stat"><span>累计作答</span><strong>{{stats.answers||0}}</strong></div><div class="stat"><span>正确率</span><strong>{{stats.accuracy||0}}%</strong></div><div class="stat"><span>当前错题</span><strong>{{stats.wrong||0}}</strong></div><div class="stat"><span>收藏题目</span><strong>{{stats.favorites||0}}</strong></div></div>
    <div class="panel">
      <div class="panel-header toolbar"><el-segmented v-model="tab" :options="tabs" /><el-select v-if="tab==='collection'" v-model="collectionId" placeholder="选择收藏夹" style="width:200px"><el-option v-for="item in collections" :key="item.id" :label="`${item.name}（${item.question_count}）`" :value="item.id" /></el-select><el-select v-else v-model="bankId" clearable placeholder="全部题库" style="width:200px"><el-option v-for="bank in store.banks" :key="bank.id" :label="bank.name" :value="bank.id" /></el-select></div>
      <el-table :data="items" v-loading="loading">
        <el-table-column label="题干" min-width="330"><template #default="{row}"><div>{{row.question.prompt}}</div><div v-if="row.note" class="note">笔记：{{row.note}}</div><div v-if="row.bank_name" class="note">{{row.bank_name}}</div></template></el-table-column>
        <el-table-column v-if="tab==='history'" label="结果" width="90"><template #default="{row}"><el-tag :type="row.is_correct?'success':row.is_correct===false?'danger':'info'">{{row.is_correct?'正确':row.is_correct===false?'错误':'自评'}}</el-tag></template></el-table-column>
        <el-table-column v-else label="错误次数" width="100"><template #default="{row}">{{row.wrong_count??'-'}}</template></el-table-column>
        <el-table-column v-if="tab!=='history'" label="状态" width="180"><template #default="{row}"><el-tag v-if="row.favorite" type="warning" effect="plain">收藏</el-tag><el-tag v-if="row.flagged" type="danger" effect="plain">待纠错</el-tag><el-tag v-if="row.mastery" effect="plain">{{row.mastery==='mastered'?'已掌握':row.mastery==='learning'?'学习中':'未学习'}}</el-tag><el-tag v-if="row.collection" effect="plain">收藏夹</el-tag></template></el-table-column>
        <el-table-column :label="tab==='history'?'作答时间':'最近作答'" width="170"><template #default="{row}">{{(row.answered_at||row.last_answered_at)?new Date(row.answered_at||row.last_answered_at).toLocaleString():'-'}}</template></el-table-column>
      </el-table><div v-if="!loading&&!items.length" class="empty">当前分类没有记录</div>
    </div>
  </section>
</template>

<style scoped>.note{margin-top:7px;color:var(--qv-muted);font-size:.82rem}.el-tag+.el-tag{margin-left:5px}</style>
