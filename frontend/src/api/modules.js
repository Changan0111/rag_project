import api from './index'

const API_BASE_URL = '/api'

export const authApi = {
  register(data) {
    return api.post('/auth/register', data)
  },

  login(data) {
    return api.post('/auth/login', {
      username: data.username,
      password: data.password,
      role: data.role
    })
  },

  getProfile() {
    return api.get('/auth/profile')
  },

  updateProfile(data) {
    return api.put('/auth/profile', data)
  },

  updatePassword(data) {
    return api.put('/auth/password', data)
  },

  uploadAvatar(file) {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/auth/avatar', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  }
}

export const chatApi = {
  sendMessage(data) {
    return api.post('/chat', data)
  },

  sendMessageStream(data, onMessage, onError, onComplete) {
    const token = localStorage.getItem('token')
    const url = `${API_BASE_URL}/chat/stream`
    let isStreamCompleted = false

    fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(data)
    })
    .then(response => {
      if (!response.ok && response.status !== 200) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      function read() {
        reader.read().then(({ done, value }) => {
          if (done) {
            isStreamCompleted = true
            if (onComplete) onComplete()
            return
          }

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

          for (const line of lines) {
            const trimmedLine = line.trim()
            if (trimmedLine.startsWith('data: ')) {
              try {
                const jsonStr = trimmedLine.slice(6)
                const eventData = JSON.parse(jsonStr)
                console.log('Received SSE event:', eventData)
                if (onMessage) onMessage(eventData)
              } catch (e) {
                console.error('Failed to parse SSE data:', e, 'Line:', trimmedLine)
              }
            }
          }

          read()
        }).catch(error => {
          console.error('SSE read error:', error)
          if (!isStreamCompleted && onError) onError(error)
        })
      }

      read()
    })
    .catch(error => {
      if (!isStreamCompleted) {
        console.error('Fetch error:', error)
        if (onError) onError(error)
      } else {
        console.log('Stream completed with normal closure')
      }
    })
  },

  getSessions(limit = 20) {
    return api.get('/chat/sessions', { params: { limit } })
  },

  getHistory(sessionId, limit = 50) {
    return api.get('/chat/history', { params: { session_id: sessionId, limit } })
  },

  clearSession(sessionId) {
    return api.delete('/chat/session', { params: { session_id: sessionId } })
  }
}

export const orderApi = {
  getList(params) {
    return api.get('/orders', { params })
  },

  getDetail(orderNo) {
    return api.get(`/orders/${orderNo}`)
  },

  getLogistics(orderNo) {
    return api.get(`/orders/${orderNo}/logistics`)
  }
}

export const knowledgeApi = {
  getList(params) {
    return api.get('/knowledge', { params })
  },

  getDetail(id) {
    return api.get(`/knowledge/${id}`)
  },

  add(data) {
    return api.post('/knowledge', data)
  },

  update(id, data) {
    return api.put(`/knowledge/${id}`, data)
  },

  delete(id) {
    return api.delete(`/knowledge/${id}`)
  },

  sync() {
    return api.post('/knowledge/sync')
  },

  getIndexStats() {
    return api.get('/knowledge/stats/index')
  },

  getSyncLogs(params) {
    return api.get('/knowledge/sync/logs', { params })
  }
}

export const statsApi = {
  getOverview() {
    return api.get('/stats/overview')
  },

  getRecentUsers(params = {}) {
    return api.get('/stats/recent-users', { params })
  },

  getHotQuestions(params) {
    return api.get('/stats/hot-questions', { params })
  },

  getChatLogs(params) {
    return api.get('/stats/chat-logs', { params })
  },

  getSessionDetail(sessionId) {
    return api.get(`/stats/session-detail/${sessionId}`)
  },

  getConversationStats() {
    return api.get('/stats/conversation-stats')
  },

  getConversationsByType(category) {
    return api.get(`/stats/conversations-by-type/${category}`)
  },

  getTodayConversations() {
    return api.get('/stats/today-conversations')
  },

  getTodayRecentMessages(params = {}) {
    return api.get('/stats/today-recent-messages', { params })
  },

  getSyncStatus() {
    return api.get('/stats/sync-status')
  },

  clearSyncLogs() {
    return api.delete('/stats/sync-logs')
  },

  getCacheStats() {
    return api.get('/stats/cache/stats')
  },

  getCacheList(params) {
    return api.get('/stats/cache/list', { params })
  },

  getCacheDetail(key) {
    return api.get(`/stats/cache/detail/${encodeURIComponent(key)}`)
  },

  deleteCacheKey(key) {
    return api.delete(`/stats/cache/key/${encodeURIComponent(key)}`)
  },

  deleteCacheKeys(keys) {
    return api.delete('/stats/cache/keys', { 
      params: { keys },
      paramsSerializer: params => {
        return keys.map(key => `keys=${encodeURIComponent(key)}`).join('&')
      }
    })
  },

  clearAllCache() {
    return api.delete('/stats/cache/clear')
  }
}

export const evaluationApi = {
  evaluateSingle(data) {
    return api.post('/evaluation/single', data, { timeout: 120000 })
  },

  evaluateBatch(data) {
    return api.post('/evaluation/batch', data, { timeout: 600000 })
  },

  compareRecallConfigs(data) {
    return api.post('/evaluation/recall-comparison', data, { timeout: 600000 })
  },

  getHistory(params) {
    return api.get('/evaluation/history', { params })
  },

  getSummary(params) {
    return api.get('/evaluation/summary', { params })
  },

  getRecords(params) {
    return api.get('/evaluation/records', { params })
  },

  getDataset() {
    return api.get('/evaluation/dataset')
  },

  addDatasetItem(data) {
    return api.post('/evaluation/dataset', data)
  },

  addDatasetItemsBatch(items) {
    return api.post('/evaluation/dataset/batch', items)
  },

  updateDatasetRelevantDocs(id, data) {
    return api.put(`/evaluation/dataset/${id}/relevant-docs`, data)
  },

  updateDatasetItem(id, data) {
    return api.put(`/evaluation/dataset/${id}`, data)
  },

  deleteDatasetItem(id) {
    return api.delete(`/evaluation/dataset/${id}`)
  },

  clearDataset() {
    return api.delete('/evaluation/dataset')
  },

  backfillEmbeddings(force = false) {
    return api.post('/evaluation/dataset/backfill-embeddings', null, { params: { force }, timeout: 300000 })
  }
}

export const ticketApi = {
  create(data) {
    return api.post('/tickets', data)
  },

  getList(params) {
    return api.get('/tickets', { params })
  },

  getPendingCount() {
    return api.get('/tickets/pending-count')
  },

  getDetail(id) {
    return api.get(`/tickets/${id}`)
  },

  getBySession(sessionId) {
    return api.get(`/tickets/by-session/${sessionId}`)
  },

  reply(id, data) {
    return api.post(`/tickets/${id}/reply`, data)
  },

  close(id) {
    return api.post(`/tickets/${id}/close`)
  },

  closeBySession(sessionId) {
    return api.post(`/tickets/user/close/${sessionId}`)
  },

  setHandling(id) {
    return api.post(`/tickets/${id}/handling`)
  },

  checkUserTicket(sessionId) {
    return api.get(`/tickets/user/check/${sessionId}`)
  }
}
