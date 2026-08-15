const token = new URLSearchParams(location.search).get('token') || sessionStorage.getItem('qv-token') || ''
if (token) sessionStorage.setItem('qv-token', token)

export async function api<T = any>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  if (token) headers.set('X-QuizVault-Token', token)
  const response = await fetch(`/api/v1${path}`, { ...options, headers })
  if (!response.ok) {
    let message = response.statusText
    try {
      const data = await response.json()
      message = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)
    } catch { /* use status text */ }
    throw new Error(message || '请求失败')
  }
  if (response.status === 204) return undefined as T
  return response.json()
}

export const jsonBody = (value: unknown): RequestInit => ({ body: JSON.stringify(value) })

export function fileAsBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result).split(',')[1] || '')
    reader.onerror = () => reject(reader.error)
    reader.readAsDataURL(file)
  })
}

