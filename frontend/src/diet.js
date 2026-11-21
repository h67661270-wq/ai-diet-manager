export const mealTypes = ['早餐', '午餐', '晚餐', '加餐']

export const defaultProfile = {
  name: '小林',
  budget: 25,
  taste: '清淡、家常',
  avoid: '',
  dining: '学校食堂',
}

export const sampleMeal = {
  title: '香煎豆腐杂粮饭',
  reason: '用豆腐搭配杂粮饭和时蔬，适合作为清淡的一餐示例。',
  items: [
    { name: '香煎豆腐', portion: '1 份' },
    { name: '杂粮饭', portion: '半碗' },
    { name: '清炒时蔬', portion: '1 份' },
  ],
  sample: true,
}

export function dateKey(date = new Date()) {
  const [month, day] = [date.getMonth() + 1, date.getDate()]
    .map(value => String(value).padStart(2, '0'))
  return [date.getFullYear(), month, day].join('-')
}

export function dayOffset(offset) {
  const date = new Date()
  date.setDate(date.getDate() + offset)
  return date
}

export function createId() {
  if (typeof crypto.randomUUID === 'function') return crypto.randomUUID()
  return [...crypto.getRandomValues(new Uint32Array(4))]
    .map(value => value.toString(16).padStart(8, '0'))
    .join('-')
}

export function seedRecords() {
  // Fictional, already-confirmed records used to demonstrate the log and charts.
  // These are never used to generate a recommendation.
  return [
    { id: 'demo-breakfast', date: dateKey(), type: '早餐', name: '燕麦酸奶碗', portion: '1 碗', energy: 320 },
    { id: 'demo-lunch', date: dateKey(), type: '午餐', name: '鸡肉时蔬饭', portion: '1 份', energy: 510 },
    { id: 'demo-yesterday', date: dateKey(dayOffset(-1)), type: '晚餐', name: '番茄豆腐面', portion: '1 碗', energy: 420 },
    { id: 'demo-three-days', date: dateKey(dayOffset(-3)), type: '午餐', name: '家常盖浇饭', portion: '1 份', energy: 580 },
    { id: 'demo-four-days', date: dateKey(dayOffset(-4)), type: '晚餐', name: '南瓜鸡肉饭', portion: '1 份', energy: 540 },
  ]
}

export const seedPosts = [
  { id: 'sample-post-1', author: '林小满', color: 'sage', title: '我的工作日轻食午餐', text: '豆腐、糙米饭和一份绿叶菜，带饭也能吃得很舒服。', likes: 8, liked: false, own: false },
  { id: 'sample-post-2', author: '周一也要吃好', color: 'peach', title: '食堂配餐的一点心得', text: '先选时蔬，再搭主菜和主食。用食堂现有的菜也能搭出不同组合。', likes: 5, liked: false, own: false },
]

export function readLocal(key, fallback) {
  try {
    const raw = localStorage.getItem(`diet-web:${key}`)
    return raw === null ? fallback : JSON.parse(raw) ?? fallback
  } catch {
    return fallback
  }
}

export function writeLocal(key, value) {
  try {
    localStorage.setItem(`diet-web:${key}`, JSON.stringify(value))
  } catch {
    return false
  }
  return true
}

export const useLiveAssistant = import.meta.env.VITE_ASSISTANT_MODE === 'api'
export const heroImage = `${import.meta.env.BASE_URL}images/diet-bowl.webp`

export async function askAssistant(message, previousMeal, recentMessages) {
  const endpoint = import.meta.env.VITE_ASSISTANT_ENDPOINT || '/api/assistant/chat'
  const response = await fetch(endpoint, {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      previous_meal: previousMeal,
      history: recentMessages.slice(-6).map(({ role, text }) => ({ role, content: text })),
    }),
    signal: AbortSignal.timeout(20000),
  })
  if (!response.ok) throw new Error('请求失败')
  const data = await response.json()
  if (typeof data.reply !== 'string' || !data.reply.trim()) throw new Error('响应格式无效')
  if (data.meal != null) {
    const meal = data.meal
    if (!Array.isArray(meal.items) || !meal.items.length || meal.items.some(
      item => !item || typeof item.name !== 'string' || typeof item.portion !== 'string',
    )) throw new Error('餐单格式无效')
    return {
      text: data.reply,
      meal: {
        title: typeof meal.title === 'string' ? meal.title : '本轮推荐',
        reason: typeof meal.reason === 'string' ? meal.reason : '',
        items: meal.items.map(({ name, portion }) => ({ name, portion })),
        sample: false,
      },
    }
  }
  return { text: data.reply, meal: null }
}
