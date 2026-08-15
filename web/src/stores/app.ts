import { defineStore } from 'pinia'
import { api } from '../api'
import type { Bank } from '../types'

export const useAppStore = defineStore('app', {
  state: () => ({ banks: [] as Bank[], loading: false, dark: localStorage.getItem('qv-dark') === '1', fontSize: Number(localStorage.getItem('qv-font') || 16) }),
  actions: {
    async loadBanks() {
      this.loading = true
      try { this.banks = await api<Bank[]>('/banks') } finally { this.loading = false }
    },
    setDark(value: boolean) {
      this.dark = value; localStorage.setItem('qv-dark', value ? '1' : '0')
      document.documentElement.classList.toggle('dark', value)
    },
    setFontSize(value: number) {
      this.fontSize = value; localStorage.setItem('qv-font', String(value))
      document.documentElement.style.setProperty('--qv-font', `${value}px`)
    },
  },
})

