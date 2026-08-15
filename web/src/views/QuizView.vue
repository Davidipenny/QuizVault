<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, ArrowRight, Back, EditPen, Flag, FolderAdd, Star } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { api, jsonBody } from '../api'
import type { Question } from '../types'

const route=useRoute(),router=useRouter(),loading=ref(true),session=ref<any>(null),index=ref(0),result=ref<any>(null),review=ref(false),noteDialog=ref(false),note=ref('')
const answer=reactive<any>({selected:[],value:true,values:[''],text:'',self_assessment:null})
const states=reactive<Record<string,{favorite:boolean;flagged:boolean;note:string}>>({})
const collections=ref<any[]>([]),collectionDialog=ref(false),newCollection=ref('')
const current=computed<Question|null>(()=>session.value?.questions[index.value]||null)
const progress=computed(()=>session.value?Math.round((Math.min(index.value+1,session.value.questions.length)/session.value.questions.length)*100):0)
const typeLabels:Record<string,string>={single:'单选题',multi:'多选题',any:'任意选',truefalse:'判断题',fill:'填空题',essay:'问答题'}
const answered=computed(()=>session.value?.answers?.find((x:any)=>x.question_id===current.value?.id))
const locked=computed(()=>!!result.value||review.value||!!answered.value)

onMounted(load)
async function load(){loading.value=true;try{[session.value,collections.value]=await Promise.all([api(`/quiz-sessions/${route.params.sessionId}`),api('/collections')]);Object.assign(states,Object.fromEntries(Object.entries(session.value.study_states||{}).map(([id,s]:any)=>[id,{favorite:s.favorite,flagged:s.flagged,note:s.note}])));index.value=Math.min(session.value.current_index,session.value.questions.length-1);restore()}catch(e:any){ElMessage.error(e.message);router.push('/quiz/setup')}finally{loading.value=false}}
function reset(){Object.assign(answer,{selected:[],value:true,values:[''],text:'',self_assessment:null});result.value=null;review.value=false}
function restore(){reset();const record=session.value?.answers?.find((x:any)=>x.question_id===current.value?.id);if(record){Object.assign(answer,JSON.parse(JSON.stringify(record.answer)));result.value={is_correct:record.is_correct,correct_answer:record.question_snapshot.answer_spec,explanation:record.question_snapshot.explanation};review.value=true}if(current.value?.type==='fill'&&!record){answer.values=(current.value.answer_spec?.blanks||['']).map(()=> '')}}
function selectChoice(label:string){if(locked.value)return;if(current.value?.type==='single')answer.selected=[label];else answer.selected=answer.selected.includes(label)?answer.selected.filter((x:string)=>x!==label):[...answer.selected,label]}
async function submit(){if(!current.value)return;try{result.value=await api(`/quiz-sessions/${session.value.id}/answers`,{method:'POST',...jsonBody({question_id:current.value.id,answer})});session.value.answers=session.value.answers.filter((x:any)=>x.question_id!==current.value?.id);session.value.answers.push({question_id:current.value.id,answer:JSON.parse(JSON.stringify(answer)),is_correct:result.value.is_correct,question_snapshot:{...current.value,answer_spec:result.value.correct_answer,explanation:result.value.explanation}});if(session.value.config.auto_next&&result.value.is_correct)setTimeout(next,650)}catch(e:any){ElMessage.error(e.message)}}
async function go(target:number){if(target<0||target>=session.value.questions.length)return;index.value=target;restore();await nextTick(()=>window.scrollTo({top:0,behavior:'smooth'}))}
function next(){if(index.value<session.value.questions.length-1)go(index.value+1);else router.push('/study')}
function prev(){if(index.value>0)go(index.value-1)}
async function patchState(payload:any){const questionId=current.value?.id;if(!questionId)return;const state=states[questionId]||{favorite:false,flagged:false,note:''};const updated=await api<any>(`/study-states/${questionId}`,{method:'PATCH',...jsonBody({...state,...payload})});states[questionId]={favorite:updated.favorite,flagged:updated.flagged,note:updated.note};ElMessage.success('已更新')}
function openNote(){const questionId=current.value?.id;if(!questionId)return;note.value=states[questionId]?.note||'';noteDialog.value=true}
async function saveNote(){await patchState({note:note.value});noteDialog.value=false}
async function addToCollection(collectionId:string){const questionId=current.value?.id;if(!questionId)return;await api(`/collections/${collectionId}/questions`,{method:'POST',...jsonBody({question_id:questionId})});collectionDialog.value=false;ElMessage.success('已加入收藏夹')}
async function createCollection(){if(!newCollection.value.trim())return;const created=await api<any>('/collections',{method:'POST',...jsonBody({name:newCollection.value})});collections.value.push(created);newCollection.value='';await addToCollection(created.id)}
function expectedText(){if(!result.value)return'';const spec=result.value.correct_answer||{};if(current.value?.type==='truefalse')return spec.value?'正确':'错误';if(['single','multi','any'].includes(current.value?.type||''))return(spec.correct||[]).join('、');if(current.value?.type==='fill')return(spec.blanks||[]).map((x:string[])=>x.join(' / ')).join('；');return spec.reference||''}
</script>

<template>
  <section class="quiz-page" v-loading="loading">
    <header class="quiz-topbar">
      <el-button text :icon="Back" @click="router.push('/quiz/setup')">退出并保存</el-button>
      <div class="progress"><span>{{index+1}} / {{session?.questions.length||0}}</span><el-progress :percentage="progress" :show-text="false" /></div>
      <div class="quiz-actions">
        <el-tooltip content="快速收藏"><el-button :icon="Star" circle plain :type="states[current?.id||'']?.favorite?'warning':''" @click="patchState({favorite:!states[current?.id||'']?.favorite})" /></el-tooltip>
        <el-tooltip content="加入收藏夹"><el-button :icon="FolderAdd" circle plain @click="collectionDialog=true" /></el-tooltip>
        <el-tooltip content="笔记"><el-button :icon="EditPen" circle plain @click="openNote" /></el-tooltip>
        <el-tooltip content="纠错标记"><el-button :icon="Flag" circle plain :type="states[current?.id||'']?.flagged?'danger':''" @click="patchState({flagged:!states[current?.id||'']?.flagged})" /></el-tooltip>
      </div>
    </header>
    <main v-if="current" class="question-area">
      <div class="question-meta"><el-tag effect="plain">{{typeLabels[current.type]}}</el-tag><span v-if="review" class="muted">回顾模式</span><span v-if="current.source" class="source">{{current.source}}</span></div>
      <div v-if="current.case_material" class="case-material">{{current.case_material}}</div>
      <h1 class="question-text">{{current.prompt}}</h1>
      <div v-if="['single','multi','any'].includes(current.type)" class="options">
        <button v-for="choice in current.choices" :key="choice.label" class="option" :class="{selected:answer.selected.includes(choice.label),locked}" :disabled="locked" @click="selectChoice(choice.label)"><span class="option-key">{{choice.label}}</span><span>{{choice.content}}</span></button>
      </div>
      <div v-else-if="current.type==='truefalse'" class="binary"><el-radio-group v-model="answer.value" :disabled="locked" size="large"><el-radio-button :value="true">正确</el-radio-button><el-radio-button :value="false">错误</el-radio-button></el-radio-group></div>
      <div v-else-if="current.type==='fill'" class="fill-list"><el-input v-for="(_,i) in answer.values" :key="i" v-model="answer.values[i]" :disabled="locked" :placeholder="`第 ${Number(i)+1} 空`"><template #prepend>{{Number(i)+1}}</template></el-input></div>
      <div v-else class="essay"><el-input v-model="answer.text" type="textarea" :rows="8" :disabled="locked" placeholder="输入你的答案" /><div v-if="!session.config.compare_essay" class="self-assess"><span>自我评价</span><el-segmented v-model="answer.self_assessment" :disabled="locked" :options="[{label:'掌握',value:true},{label:'未掌握',value:false}]" /></div></div>
      <div v-if="result" class="feedback" :class="result.is_correct===true?'correct':result.is_correct===false?'wrong':'neutral'">
        <strong>{{result.is_correct===true?'回答正确':result.is_correct===false?'回答错误':'已记录'}}</strong>
        <div><span class="feedback-label">参考答案</span><span class="question-text">{{expectedText()}}</span></div>
        <div v-if="result.explanation"><span class="feedback-label">解析</span><span class="question-text">{{result.explanation}}</span></div>
      </div>
    </main>
    <footer v-if="current" class="quiz-footer">
      <el-button :icon="ArrowLeft" :disabled="index===0" @click="prev">上一题</el-button>
      <el-button v-if="!locked" type="primary" size="large" @click="submit">提交答案</el-button>
      <el-button v-else type="primary" size="large" @click="next">{{index===session.questions.length-1?'查看学习记录':'下一题'}}<el-icon class="el-icon--right"><ArrowRight /></el-icon></el-button>
    </footer>
    <el-dialog v-model="noteDialog" title="题目笔记" width="min(560px,92vw)"><el-input v-model="note" type="textarea" :rows="8" placeholder="记录思路或易错点" /><template #footer><el-button @click="noteDialog=false">取消</el-button><el-button type="primary" @click="saveNote">保存笔记</el-button></template></el-dialog>
    <el-dialog v-model="collectionDialog" title="加入收藏夹" width="min(460px,92vw)"><div class="collection-list"><el-button v-for="item in collections" :key="item.id" plain @click="addToCollection(item.id)">{{item.name}}（{{item.question_count}}）</el-button><el-input v-model="newCollection" placeholder="新收藏夹名称" @keyup.enter="createCollection"><template #append><el-button @click="createCollection">新建并加入</el-button></template></el-input></div></el-dialog>
  </section>
</template>

<style scoped>
.quiz-page{max-width:980px;margin:0 auto}.quiz-topbar{display:grid;grid-template-columns:180px 1fr 180px;align-items:center;gap:20px;margin-bottom:34px}.progress{display:grid;grid-template-columns:auto 1fr;gap:12px;align-items:center}.quiz-actions{display:flex;justify-content:flex-end;gap:8px}.question-area{min-height:540px}.question-meta{display:flex;align-items:center;gap:12px;margin-bottom:16px}.source{margin-left:auto;color:var(--qv-muted);font-size:.8rem}.case-material{padding:16px 18px;border-left:3px solid var(--qv-accent);background:var(--qv-panel);line-height:1.75;margin-bottom:18px}.question-area h1{font-size:1.35rem;font-weight:650;line-height:1.75;margin:0 0 26px}.options{display:grid;gap:12px}.option{display:grid;grid-template-columns:38px 1fr;gap:12px;align-items:center;width:100%;min-height:58px;padding:10px 16px;text-align:left;color:inherit;background:var(--qv-panel);border:1px solid var(--qv-border);border-radius:6px;cursor:pointer}.option:hover:not(:disabled){border-color:#58aea3;background:#f2faf8}.dark .option:hover:not(:disabled){background:#17302d}.option.selected{border-color:var(--qv-accent);background:var(--qv-accent-soft)}.dark .option.selected{background:#193a36}.option-key{display:grid;place-items:center;width:30px;height:30px;border:1px solid #aeb9bd;border-radius:50%;font-weight:650}.option.selected .option-key{background:var(--qv-accent);border-color:var(--qv-accent);color:white}.fill-list{display:grid;gap:12px}.self-assess{display:flex;align-items:center;justify-content:space-between;margin-top:14px}.feedback{margin-top:26px;padding:18px;border:1px solid;border-radius:6px}.feedback.correct{background:#eff8f3;border-color:#a6d5bb}.feedback.wrong{background:#fdf3f2;border-color:#e3b3ae}.dark .feedback.correct{background:#183126}.dark .feedback.wrong{background:#382321}.feedback>strong{display:block;margin-bottom:14px}.feedback>div{display:grid;grid-template-columns:90px 1fr;gap:12px;margin-top:10px}.feedback-label{color:var(--qv-muted)}.quiz-footer{display:flex;align-items:center;justify-content:space-between;padding-top:20px;border-top:1px solid var(--qv-border)}@media(max-width:700px){.quiz-topbar{grid-template-columns:1fr auto}.progress{grid-column:1/-1;grid-row:2}.quiz-actions{grid-column:2}.question-area{min-height:480px}.feedback>div{grid-template-columns:1fr;gap:4px}}
.collection-list{display:grid;gap:10px}.collection-list>.el-button{margin:0;justify-content:flex-start}
</style>
