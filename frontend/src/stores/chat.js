import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useChatStore = defineStore('chat', () => {
  const savedSession = localStorage.getItem('chat_session')
  const savedMessages = localStorage.getItem('chat_messages')
  
  const sessionId = ref(savedSession || '')
  const messages = ref(savedMessages ? JSON.parse(savedMessages) : [])

  function initSession() {
    sessionId.value = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9)
    messages.value = []
    localStorage.setItem('chat_session', sessionId.value)
    localStorage.setItem('chat_messages', JSON.stringify(messages.value))
  }

  function addMessage(role, content, source = 'bot', sources = []) {
    messages.value.push({
      role,
      content,
      source,
      sources,
      timestamp: new Date().toISOString()
    })
    localStorage.setItem('chat_messages', JSON.stringify(messages.value))
  }

  function clearMessages() {
    messages.value = []
    localStorage.setItem('chat_messages', JSON.stringify(messages.value))
  }

  function setMessages(newMessages) {
    messages.value = JSON.parse(JSON.stringify(newMessages))
    localStorage.setItem('chat_messages', JSON.stringify(messages.value))
  }

  function setSessionId(newSessionId) {
    sessionId.value = newSessionId
    localStorage.setItem('chat_session', sessionId.value)
  }

  if (!sessionId.value) {
    initSession()
  }

  return {
    sessionId,
    messages,
    initSession,
    addMessage,
    clearMessages,
    setMessages,
    setSessionId
  }
})
