import { defineStore } from 'pinia'
import { ref } from 'vue'
import { chatApi } from '@/api/modules'

export const useSessionStore = defineStore('session', () => {
  const sessions = ref([])
  const loading = ref(false)

  async function fetchSessions() {
    loading.value = true
    try {
      const data = await chatApi.getSessions()
      sessions.value = data
    } catch (error) {
      console.error('获取会话列表失败:', error)
    } finally {
      loading.value = false
    }
  }

  function addSession(session) {
    const existingIndex = sessions.value.findIndex(s => s.session_id === session.session_id)
    if (existingIndex >= 0) {
      sessions.value.splice(existingIndex, 1)
      sessions.value.unshift(session)
    } else {
      sessions.value.unshift(session)
    }
  }

  function removeSession(sessionId) {
    sessions.value = sessions.value.filter(s => s.session_id !== sessionId)
  }

  return {
    sessions,
    loading,
    fetchSessions,
    addSession,
    removeSession
  }
})
