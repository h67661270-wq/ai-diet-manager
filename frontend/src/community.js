import { getPhoto } from './photos'

export async function fetchPosts() {
  const response = await fetch('/api/posts', { signal: AbortSignal.timeout(5000) })
  if (!response.ok) throw new Error('社区暂时无法连接。')
  const posts = await response.json()
  if (!Array.isArray(posts)) throw new Error('社区响应格式错误。')
  return posts
}

export async function publishPost({ id, author, title, text, photo, photoId }) {
  const body = new FormData()
  body.append('post_id', id)
  body.append('author', author)
  body.append('title', title)
  body.append('text', text)
  const image = photo ?? (photoId ? await getPhoto(photoId) : null)
  if (photoId && !image) throw new Error('无法读取已有照片，请重新添加配图。')
  if (image) body.append('file', image, 'meal')
  try {
    const response = await fetch('/api/posts', {
      method: 'POST', body, signal: AbortSignal.timeout(20000),
    })
    if (response.ok) return await response.json()
  } catch {
    // The same post ID is reused on retry if the first response was lost.
  }
  throw new Error('帖子发布失败，请检查后端连接并重试。')
}
