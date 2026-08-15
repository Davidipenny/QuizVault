import { createRouter, createWebHashHistory } from 'vue-router'
export default createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', redirect: '/banks' },
    { path: '/banks', component: () => import('./views/BanksView.vue') },
    { path: '/banks/:bankId/questions', component: () => import('./views/QuestionsView.vue') },
    { path: '/import', component: () => import('./views/ImportView.vue') },
    { path: '/quiz/setup', component: () => import('./views/QuizSetupView.vue') },
    { path: '/quiz/:sessionId', component: () => import('./views/QuizView.vue') },
    { path: '/study', component: () => import('./views/StudyView.vue') },
    { path: '/settings', component: () => import('./views/SettingsView.vue') },
  ],
})
