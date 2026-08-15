<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { Collection, DataAnalysis, DocumentAdd, Files, Reading, Setting } from '@element-plus/icons-vue'
import { useAppStore } from './stores/app'

const route = useRoute()
const store = useAppStore()
onMounted(() => { store.setDark(store.dark); store.setFontSize(store.fontSize); store.loadBanks() })
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="brand"><span class="brand-mark">QV</span><strong>QuizVault</strong></div>
      <el-menu router :default-active="route.path" class="nav-menu">
        <el-menu-item index="/banks"><el-icon><Files /></el-icon><span>题库中心</span></el-menu-item>
        <el-menu-item index="/import"><el-icon><DocumentAdd /></el-icon><span>录题中心</span></el-menu-item>
        <el-menu-item index="/quiz/setup"><el-icon><Reading /></el-icon><span>开始刷题</span></el-menu-item>
        <el-menu-item index="/study"><el-icon><DataAnalysis /></el-icon><span>学习记录</span></el-menu-item>
        <el-menu-item index="/settings"><el-icon><Setting /></el-icon><span>数据与设置</span></el-menu-item>
      </el-menu>
      <div class="sidebar-foot"><el-icon><Collection /></el-icon><span>{{ store.banks.length }} 个题库</span></div>
    </aside>
    <main class="main"><router-view /></main>
  </div>
</template>

