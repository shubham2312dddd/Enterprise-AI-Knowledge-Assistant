import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000',
  timeout: 30000,
})

export async function checkBackendHealth() {
  const response = await api.get('/health')
  return response.data
}

export async function uploadPdf(file, onProgress) {
  const formData = new FormData()
  formData.append('file', file)

  const response = await api.post('/api/documents/upload', formData, {
    onUploadProgress: (event) => {
      if (event.total) {
        onProgress(Math.round((event.loaded * 100) / event.total))
      }
    },
  })

  return response.data
}

export async function listDocuments() {
  const response = await api.get('/api/documents')
  return response.data
}

export async function deleteDocument(documentId) {
  const response = await api.delete(`/api/documents/${encodeURIComponent(documentId)}`)
  return response.data
}

export async function searchDocuments(query, documentIds = null, topK = 3) {
  const response = await api.post('/api/search', {
    query,
    top_k: topK,
    document_ids: documentIds,
  })
  return response.data
}

export async function searchDocument(documentId, query, topK = 3) {
  const response = await api.post(
    `/api/documents/${encodeURIComponent(documentId)}/search`,
    { query, top_k: topK },
  )
  return response.data
}

export async function chatWithDocuments(question, documentIds = null, topK = 3) {
  const response = await api.post('/api/chat', {
    question,
    document_ids: documentIds,
    top_k: topK,
  }, {
    timeout: 180000,
  })

  return response.data
}

export function getApiErrorMessage(error) {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') {
      return detail
    }
    if (Array.isArray(detail)) {
      const messages = detail
        .map((item) => (typeof item?.msg === 'string' ? item.msg : ''))
        .filter(Boolean)
      if (messages.length > 0) {
        return messages.join(' ')
      }
    }
    if (!error.response) {
      return 'Could not reach the backend. Check that the API is running and try again.'
    }
  }

  return 'Something went wrong while contacting the assistant. Please try again.'
}
