import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const userInfo = ref(JSON.parse(localStorage.getItem('userInfo') || 'null'))
  const role = ref(localStorage.getItem('userRole') || 'user')

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => role.value === 'admin')

  function setToken(newToken) {
    token.value = newToken
    localStorage.setItem('token', newToken)
  }

  function setUserInfo(info) {
    userInfo.value = info
    localStorage.setItem('userInfo', JSON.stringify(info))
  }

  function setRole(newRole) {
    role.value = newRole
    localStorage.setItem('userRole', newRole)
  }

  function logout() {
    token.value = ''
    userInfo.value = null
    role.value = 'user'
    localStorage.removeItem('token')
    localStorage.removeItem('userInfo')
    localStorage.removeItem('userRole')
    localStorage.removeItem('chat_session')
    localStorage.removeItem('chat_messages')
  }

  return {
    token,
    userInfo,
    role,
    isLoggedIn,
    isAdmin,
    setToken,
    setUserInfo,
    setRole,
    logout
  }
})
