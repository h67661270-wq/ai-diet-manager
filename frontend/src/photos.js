import { createId, heroImage } from './diet'

export const photoAccept = 'image/jpeg,image/png,image/webp'
const maxInputBytes = 15 * 1024 * 1024

export const nutrientLabels = {
  energy_kcal: { label: '能量', unit: 'kcal' },
  protein_g: { label: '蛋白质', unit: 'g' },
  fat_g: { label: '脂肪', unit: 'g' },
  carbs_g: { label: '碳水', unit: 'g' },
}

export function formatNutrient(value) {
  return typeof value === 'number' ? new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 1 }).format(value) : '未知'
}

export async function preparePhoto(file) {
  if (!photoAccept.split(',').includes(file.type)) {
    throw new Error('请选择 JPG、PNG 或 WebP 图片。')
  }
  if (file.size > maxInputBytes) throw new Error('图片最大支持 15 MB。')

  let bitmap
  try {
    bitmap = await createImageBitmap(file)
  } catch {
    throw new Error('无法读取这张图片，请换一张。')
  }
  try {
    const scale = Math.min(1, 1280 / Math.max(bitmap.width, bitmap.height))
    const canvas = document.createElement('canvas')
    canvas.width = Math.max(1, Math.round(bitmap.width * scale))
    canvas.height = Math.max(1, Math.round(bitmap.height * scale))
    const context = canvas.getContext('2d', { alpha: false })
    if (!context) throw new Error('当前浏览器无法处理图片。')
    context.fillStyle = '#fff'
    context.fillRect(0, 0, canvas.width, canvas.height)
    context.drawImage(bitmap, 0, 0, canvas.width, canvas.height)
    const photo = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.84))
    if (!photo) throw new Error('图片压缩失败，请换一张。')
    return photo
  } finally {
    bitmap.close()
  }
}

export async function analyzeMeal(photo, signal, mealHint = '') {
  const body = new FormData()
  body.append('file', photo, 'meal.jpg')
  if (mealHint) body.append('meal_hint', mealHint)
  let response
  try {
    response = await fetch('/api/meal-analysis', { method: 'POST', body, signal })
  } catch (error) {
    if (signal.aborted) throw error
    throw new Error('未连接到照片分析服务。请检查后端是否启动。')
  }
  const data = await response.json().catch(() => null)
  if (!response.ok) {
    throw new Error(typeof data?.detail === 'string'
      ? data.detail
      : '未连接到照片分析服务。请检查后端是否启动。')
  }
  if (!data?.foods?.length || !data.totals) throw new Error('未收到有效的餐食分析。')
  return data
}

export async function loadExampleAnalysis() {
  const response = await fetch(heroImage)
  if (!response.ok) throw new Error('示例照片加载失败。')
  return {
    photo: await response.blob(),
    analysis: {
      foods: [
        { name: '香煎豆腐', category: '豆制品', portion: '约 120 g' },
        { name: '杂粮饭', category: '主食', portion: '约 140 g' },
        { name: '时蔬', category: '蔬菜', portion: '约 100 g' },
      ],
      totals: { energy_kcal: 460, protein_g: 19, fat_g: 17, carbs_g: 59 },
      notes: '这是一份示例分析，用于体验打卡流程。',
    },
  }
}

function openPhotoDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('diet-web-media', 1)
    request.onupgradeneeded = () => request.result.createObjectStore('photos')
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

async function withPhotos(mode, operation) {
  const database = await openPhotoDB()
  try {
    return await new Promise((resolve, reject) => {
      const transaction = database.transaction('photos', mode)
      const request = operation(transaction.objectStore('photos'))
      transaction.oncomplete = () => resolve(request.result)
      transaction.onabort = () => reject(transaction.error ?? request.error)
    })
  } finally {
    database.close()
  }
}

export async function savePhoto(blob) {
  const id = createId()
  await withPhotos('readwrite', photos => photos.add(blob, id))
  return id
}

export function getPhoto(id) {
  return withPhotos('readonly', photos => photos.get(id))
}

export function removePhoto(id) {
  return withPhotos('readwrite', photos => photos.delete(id))
}

