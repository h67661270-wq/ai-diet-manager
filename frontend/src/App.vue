<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import {
  ArrowUp, BarChart3, BookOpen, CalendarDays, Check, CircleCheck, ClipboardList,
  Heart, LayoutGrid, Leaf, MessageCircle, Plus, Settings2, Sparkles,
  Sun, Utensils, UtensilsCrossed, X,
} from '@lucide/vue'
import {
  askAssistant, createId, dateKey, dayOffset, defaultProfile, heroImage, mealTypes,
  readLocal, sampleMeal, seedPosts, seedRecords, useLiveAssistant, writeLocal,
} from './diet'

const navigation = [
  { key: 'assistant', label: 'AI 饮食助手', icon: MessageCircle, description: '个性化推荐与饮食记录' },
  { key: 'journal', label: '日常打卡', icon: CalendarDays, description: '记录每一餐的食物和份量' },
  { key: 'stats', label: '健康统计', icon: BarChart3, description: '回顾最近的饮食与打卡趋势' },
  { key: 'community', label: '社区分享', icon: LayoutGrid, description: '分享用户自选的餐食和心得' },
  { key: 'profile', label: '个人档案', icon: Settings2, description: '管理助手推荐时参考的偏好' },
]

function readView() {
  const hash = window.location.hash.slice(1)
  return navigation.some(item => item.key === hash) ? hash : 'assistant'
}

const view = ref(readView())
const activeNav = computed(() => navigation.find(item => item.key === view.value))
function navigate(key) {
  if (key !== view.value) {
    view.value = key
    window.location.hash = key
    window.scrollTo(0, 0)
  }
}
function onHashChange() {
  view.value = readView()
  window.scrollTo(0, 0)
}

const profile = ref(readLocal('profile', { ...defaultProfile }))
const profileDraft = ref({ ...profile.value })
const logs = ref(readLocal('logs', seedRecords()))
const posts = ref(readLocal('posts', seedPosts.map(post => ({ ...post }))))
const savedMeals = ref(readLocal('meals', []))
const toast = ref('')
let toastTimer
function notify(message) {
  toast.value = message
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toast.value = '' }, 3500)
}

function persist(key, value, message) {
  notify(writeLocal(key, value) ? message : '浏览器存储不可用，改动仅在当前页面保留。')
}

const today = dateKey()
const dateLabel = new Intl.DateTimeFormat('zh-CN', { month: 'long', day: 'numeric', weekday: 'long' }).format()
const firstName = computed(() => profile.value.name.trim() || '你好')
const todayLogs = computed(() => logs.value.filter(log => log.date === today))
const todayEnergy = computed(() => totalEnergy(todayLogs.value))
const weekDays = computed(() => Array.from({ length: 7 }, (_, index) => {
  const date = dayOffset(index - 6)
  const key = dateKey(date)
  const records = logs.value.filter(log => log.date === key)
  return {
    key, count: records.length, energy: totalEnergy(records),
    label: new Intl.DateTimeFormat('zh-CN', { weekday: 'short' }).format(date).replace('周', ''),
  }
}))
const weekRecords = computed(() => weekDays.value.reduce((sum, day) => sum + day.count, 0))
const weekActive = computed(() => weekDays.value.filter(day => day.count > 0).length)
const weekMax = computed(() => Math.max(1, ...weekDays.value.map(day => day.energy ?? 0)))
const filter = ref('全部')
const sortedLogs = computed(() => [...logs.value].sort((a, b) => b.date.localeCompare(a.date)))
const displayedLogs = computed(() => sortedLogs.value.filter(log => filter.value === '全部' || log.type === filter.value))

function totalEnergy(records) {
  const known = records.filter(log => typeof log.energy === 'number')
  return known.length ? known.reduce((sum, log) => sum + log.energy, 0) : null
}

function displayDate(key) {
  return key === today ? '今天' : key.slice(5).replace('-', '/')
}

const quickPrompts = [
  '今晚 25 元以内吃什么？',
  '想吃清淡一点，帮我搭配',
  '帮我搭配一份素食午餐',
]
const conversation = ref([])
const message = ref('')
const currentMeal = ref(null)
const busy = ref(false)
const chatError = ref('')
const chatInput = ref(null)
const chatLog = ref(null)

function focusChat() {
  nextTick(() => chatInput.value?.focus())
}

function scrollChat() {
  nextTick(() => {
    if (chatLog.value) chatLog.value.scrollTop = chatLog.value.scrollHeight
  })
}

function selectPrompt(prompt) {
  message.value = prompt
  focusChat()
}

function handleChatKey(event) {
  if (event.key !== 'Enter' || event.shiftKey || event.isComposing || event.keyCode === 229) return
  event.preventDefault()
  sendMessage()
}

async function sendMessage() {
  const text = message.value.trim()
  if (!text || busy.value) return
  const recent = [...conversation.value]
  conversation.value.push({ id: createId(), role: 'user', text })
  message.value = ''
  chatError.value = ''
  scrollChat()
  if (!useLiveAssistant) {
    conversation.value.push({
      id: createId(),
      role: 'assistant',
      text: '这是本地演示。你可以打开示例餐单，体验保存、打卡和分享。',
    })
    scrollChat()
    return
  }
  busy.value = true
  try {
    const result = await askAssistant(text, currentMeal.value, recent)
    conversation.value.push({ id: createId(), role: 'assistant', text: result.text })
    if (result.meal) currentMeal.value = result.meal
  } catch {
    message.value = text
    chatError.value = '助手暂时无法回复，请检查后端连接并重试。'
  } finally {
    busy.value = false
    scrollChat()
  }
}

function showSampleMeal() {
  currentMeal.value = sampleMeal
  conversation.value.push({
    id: createId(), role: 'assistant',
    text: '已打开示例餐单。可以先保存方案，或点击「记入打卡」确认实际份量。',
  })
  scrollChat()
}

function keepMeal() {
  const meal = currentMeal.value
  if (!meal) return
  const signature = JSON.stringify(meal.items)
  if (savedMeals.value.some(saved => saved.signature === signature)) {
    notify('这份餐单已保存。')
    return
  }
  savedMeals.value.push({ ...meal, id: createId(), signature })
  persist('meals', savedMeals.value, '已保存到饮食记录。')
}

function useSavedMeal(meal) {
  currentMeal.value = meal
  navigate('assistant')
}

const dialog = ref(null)
const dialogType = ref('')
const logDraft = ref({})
const shareDraft = ref({})
const sharedLog = computed(() => logs.value.find(log => log.id === shareDraft.value.logId))

function openLog(meal = null) {
  const portion = meal?.items.map(item => `${item.name} ${item.portion}`).join('、') ?? ''
  logDraft.value = { name: meal?.title ?? '', portion, type: '晚餐', date: today, energy: '' }
  dialogType.value = 'log'
  nextTick(() => dialog.value?.showModal())
}

function confirmLog() {
  const draft = logDraft.value
  if (!draft.name.trim() || !draft.portion.trim()) return
  if (draft.date > today) {
    notify('请选择今天或更早的日期。')
    return
  }
  logs.value.unshift({
    id: createId(), name: draft.name.trim(), portion: draft.portion.trim(),
    type: draft.type, date: draft.date, energy: draft.energy === '' ? null : Number(draft.energy),
  })
  dialog.value?.close()
  persist('logs', logs.value, '打卡成功，统计已更新。')
}

function openShare(log = null) {
  if (!logs.value.some(entry => !entry.id.startsWith('demo-'))) {
    notify('先记录一餐，就能发布你的餐食分享。')
    navigate('journal')
    return
  }
  shareDraft.value = { logId: log?.id ?? sortedLogs.value.find(entry => !entry.id.startsWith('demo-')).id, text: '' }
  dialogType.value = 'share'
  nextTick(() => dialog.value?.showModal())
}

function confirmShare() {
  if (!sharedLog.value || sharedLog.value.id.startsWith('demo-')) return
  posts.value.unshift({
    id: createId(), author: firstName.value, color: 'sage',
    title: sharedLog.value.name, text: shareDraft.value.text.trim() || '分享了今天的一餐。',
    likes: 0, liked: false, own: true,
  })
  dialog.value?.close()
  navigate('community')
  persist('posts', posts.value, '分享已发布到本地社区。')
}

function toggleLike(post) {
  post.liked = !post.liked
  post.likes += post.liked ? 1 : -1
  writeLocal('posts', posts.value)
}

function confirmProfile() {
  profile.value = { ...profileDraft.value, name: profileDraft.value.name.trim() || '小林' }
  profileDraft.value = { ...profile.value }
  persist('profile', profile.value, '档案已保存到此浏览器。')
}

watch(view, key => {
  if (key === 'profile') profileDraft.value = { ...profile.value }
})
onMounted(() => window.addEventListener('hashchange', onHashChange))
onUnmounted(() => {
  window.removeEventListener('hashchange', onHashChange)
  clearTimeout(toastTimer)
})
</script>

<template>
  <div class="shell">
    <aside class="sidebar">
      <a class="brand" href="#assistant" aria-label="食合首页" @click.prevent="navigate('assistant')">
        <span class="brand-symbol"><Leaf :size="22" :stroke-width="2" /></span>
        <span class="brand-name">食合</span>
      </a>
      <nav class="navigation" aria-label="主导航">
        <a v-for="item in navigation" :key="item.key" :href="`#${item.key}`"
          :aria-label="item.label" :aria-current="view === item.key ? 'page' : undefined" @click.prevent="navigate(item.key)">
          <component :is="item.icon" :size="20" :stroke-width="1.8" />
          <span>{{ item.label }}</span>
        </a>
      </nav>
      <button class="account" type="button" aria-label="管理我的偏好" @click="navigate('profile')">
        <span class="avatar">{{ firstName.slice(0, 1) }}</span>
        <span class="account-copy"><strong>{{ firstName }}</strong><small>管理我的偏好</small></span>
        <Settings2 :size="16" class="account-gear" />
      </button>
    </aside>

    <main class="main">
      <header class="topbar">
        <div><p class="crumb">饮食管理</p><h1>{{ activeNav.label }}</h1></div>
        <div class="topbar-meta">
          <span class="mode"><span></span>{{ useLiveAssistant ? '模型模式' : '本地演示' }}</span>
          <span class="topbar-date"><CalendarDays :size="17" />{{ dateLabel }}</span>
          <button v-if="view !== 'profile'" class="button primary topbar-action" type="button" @click="openLog()"><Plus :size="18" />记一餐</button>
        </div>
      </header>

      <div v-if="view === 'assistant'" class="content dashboard">
        <section class="hero" aria-labelledby="hero-title">
          <img class="hero-image" :src="heroImage" alt="" fetchpriority="high" />
          <div class="hero-copy">
            <p class="hero-eyebrow"><Sun :size="16" />{{ firstName }}，欢迎回来</p>
            <h2 id="hero-title">今天，吃点什么？</h2>
            <p class="hero-description">告诉助手你的预算、口味和忌口，一起搭配今天的一餐。</p>
            <button class="button hero-button" type="button" @click="focusChat"><MessageCircle :size="17" />开始对话</button>
          </div>
        </section>

        <div class="dashboard-grid">
          <section class="card assistant-card" aria-labelledby="assistant-title">
            <header class="card-head assistant-head">
              <span class="icon-tile green"><Sparkles :size="20" /></span>
              <div><h2 id="assistant-title">饮食助手</h2><p>按你的需求生成餐单</p></div>
              <button v-if="!useLiveAssistant" class="button quiet sample-button" type="button" @click="showSampleMeal">试用示例餐单</button>
            </header>
            <div ref="chatLog" class="chat-log" role="log" aria-label="对话记录" aria-live="polite">
              <div class="message assistant-message"><span class="message-mark"><Sparkles :size="15" /></span>
                <div class="bubble"><strong>你好，我是你的饮食助手。</strong><p>说说这餐想吃什么，或者告诉我需要避开的食材和预算。</p></div>
              </div>
              <div v-for="entry in conversation" :key="entry.id" class="message" :class="entry.role === 'user' ? 'user-message' : 'assistant-message'">
                <span v-if="entry.role === 'assistant'" class="message-mark"><Sparkles :size="15" /></span>
                <div class="bubble"><p>{{ entry.text }}</p></div>
              </div>
              <p v-if="busy" class="chat-status">正在生成餐单…</p>
            </div>
            <form class="composer" @submit.prevent="sendMessage">
              <div v-if="!conversation.length" class="quick-prompts" aria-label="示例问题">
                <button v-for="prompt in quickPrompts" :key="prompt" type="button" @click="selectPrompt(prompt)">{{ prompt }}</button>
              </div>
              <p v-if="chatError" class="form-error" role="alert">{{ chatError }}</p>
              <div class="input-wrap">
                <textarea ref="chatInput" v-model="message" rows="2" maxlength="600" aria-label="给饮食助手发消息"
                  placeholder="例如：今晚 25 元以内，想吃清淡一点…" @keydown="handleChatKey"></textarea>
                <button class="send" type="submit" :disabled="!message.trim() || busy" aria-label="发送消息"><ArrowUp :size="21" /></button>
              </div>
              <p class="composer-hint">{{ useLiveAssistant ? '生成的营养或价格信息仅供参考。' : '本地演示可试用示例餐单。' }}</p>
            </form>
          </section>

          <aside class="right-column" aria-label="饮食概览">
            <section v-if="currentMeal" class="card side-card meal-card">
              <header class="section-head">
                <span class="icon-tile amber"><Utensils :size="18" /></span>
                <div><h2>{{ currentMeal.title }}</h2><p>{{ currentMeal.sample ? '示例餐单' : '本轮推荐' }}</p></div>
              </header>
              <p v-if="currentMeal.reason" class="meal-reason">{{ currentMeal.reason }}</p>
              <ul class="meal-items"><li v-for="(item, idx) in currentMeal.items" :key="idx"><span>{{ item.name }}</span><strong>{{ item.portion }}</strong></li></ul>
              <div class="meal-actions">
                <button class="button quiet" type="button" @click="keepMeal"><BookOpen :size="16" />保存方案</button>
                <button class="button primary" type="button" @click="openLog(currentMeal)"><Check :size="17" />记入打卡</button>
              </div>
            </section>
            <section v-else class="card side-card today-card">
              <header class="section-head"><span class="icon-tile amber"><ClipboardList :size="19" /></span><div><h2>今日打卡</h2><p>只统计已确认的记录</p></div></header>
              <div class="today-summary">
                <div><strong>{{ todayLogs.length }}</strong><span>餐已记录</span></div>
                <div><strong>{{ todayEnergy ?? '—' }}</strong><span>已记录 kcal</span></div>
              </div>
              <ul class="timeline">
                <li v-for="label in mealTypes.slice(0, 3)" :key="label">
                  <CircleCheck v-if="todayLogs.some(log => log.type === label)" :size="17" class="checked" />
                  <span v-else class="empty-circle"></span><span>{{ label }}</span>
                  <small>{{ todayLogs.some(log => log.type === label) ? '已打卡' : '待记录' }}</small>
                </li>
              </ul>
            </section>
            <section class="card side-card week-card">
              <header class="section-head">
                <span class="icon-tile green"><BarChart3 :size="18" /></span>
                <div><h2>近 7 天记录</h2><p>已打卡 {{ weekActive }} 天</p></div>
                <button class="text-button" type="button" @click="navigate('stats')">详情</button>
              </header>
              <div class="spark-chart" role="img" :aria-label="`近七天每日打卡餐数 ${weekDays.map(day => day.count).join('、')}`">
                <div v-for="day in weekDays" :key="day.key" class="spark-day">
                  <div class="spark-track"><i :class="{ 'no-data': !day.count, 'is-today': day.key === today }"
                    :style="{ height: day.count ? `${Math.min(100, day.count * 34 + 15)}%` : '7px' }"></i></div><span>{{ day.label }}</span>
                </div>
              </div>
            </section>
          </aside>
        </div>
      </div>

      <div v-else class="content module">
        <header class="module-header">
          <span class="icon-tile green"><component :is="activeNav.icon" :size="24" /></span>
          <div><h2>{{ activeNav.label }}</h2><p>{{ activeNav.description }}</p></div>
        </header>

        <template v-if="view === 'journal'">
          <section class="card module-card">
            <div class="module-toolbar"><h3>饮食记录</h3><label>餐别 <select v-model="filter"><option>全部</option><option v-for="type in mealTypes" :key="type">{{ type }}</option></select></label></div>
            <div v-if="displayedLogs.length" class="table-scroll">
              <table><thead><tr><th>日期</th><th>餐别</th><th>餐食</th><th>份量</th><th>能量</th><th>操作</th></tr></thead>
                <tbody><tr v-for="log in displayedLogs" :key="log.id">
                  <td>{{ displayDate(log.date) }}</td><td>{{ log.type }}</td><td><strong>{{ log.name }}</strong></td>
                  <td>{{ log.portion }}</td><td>{{ log.energy === null ? '未填写' : `${log.energy} kcal` }}</td>
                  <td><button v-if="!log.id.startsWith('demo-')" class="text-button" type="button" @click="openShare(log)">分享</button><small v-else>示例</small></td>
                </tr></tbody>
              </table>
            </div>
            <p v-else class="empty">这个餐别暂无记录。</p>
          </section>
          <section class="card module-card">
            <div class="module-toolbar"><h3>保存的餐单</h3></div>
            <p v-if="!savedMeals.length" class="empty">你保存的方案会显示在这里。</p>
            <ul v-else class="saved-list"><li v-for="meal in savedMeals" :key="meal.id">
              <span><strong>{{ meal.title }}</strong><small>{{ meal.items.map(item => item.name).join(' · ') }}</small></span>
              <button class="button quiet" type="button" @click="useSavedMeal(meal)">查看餐单</button>
            </li></ul>
          </section>
        </template>

        <template v-else-if="view === 'stats'">
          <section class="stat-tiles">
            <div class="card stat-tile"><p>近 7 天打卡</p><strong>{{ weekActive }} <small>天</small></strong></div>
            <div class="card stat-tile"><p>近 7 天已记餐食</p><strong>{{ weekRecords }} <small>餐</small></strong></div>
            <div class="card stat-tile"><p>今日已记录能量</p><strong>{{ todayEnergy ?? '—' }} <small>kcal</small></strong></div>
          </section>
          <section class="card module-card">
            <div class="module-toolbar"><h3>近 7 天已记录能量</h3><small>只汇总填写了能量的餐食</small></div>
            <div class="energy-chart" role="img" :aria-label="weekDays.map(day => `${day.key} ${day.energy ?? '未记录'}`).join('，')">
              <div class="energy-day" v-for="day in weekDays" :key="day.key">
                <div class="energy-track"><i :class="{ 'no-data': day.energy === null, 'is-today': day.key === today }"
                  :style="{ height: day.energy === null ? '6px' : `max(3px, ${day.energy / weekMax * 100}%)` }"><span>{{ day.energy ?? '未记录' }}</span></i></div>
                <small>{{ day.key.slice(5).replace('-', '/') }}</small>
              </div>
            </div>
          </section>
        </template>

        <template v-else-if="view === 'community'">
          <div class="community-toolbar"><h3>餐食动态</h3><button class="button primary" type="button" @click="openShare()"><Plus :size="18" />分享一餐</button></div>
          <article v-for="post in posts" :key="post.id" class="card module-card post">
            <header class="post-author"><span class="avatar" :class="post.color">{{ post.author.slice(0, 1) }}</span><div><strong>{{ post.author }}</strong><small>{{ post.own ? '我的分享' : '演示帖子' }}</small></div></header>
            <h3>{{ post.title }}</h3><p>{{ post.text }}</p>
            <button class="button quiet like" :class="{ liked: post.liked }" :aria-pressed="post.liked" type="button" @click="toggleLike(post)"><Heart :size="17" :fill="post.liked ? 'currentColor' : 'none'" />{{ post.likes }} 点赞</button>
          </article>
        </template>

        <form v-else class="card module-card profile-form" @submit.prevent="confirmProfile">
          <div class="module-toolbar"><h3>用餐偏好</h3><small>保存在当前浏览器</small></div>
          <div class="field-grid">
            <label>称呼<input v-model="profileDraft.name" maxlength="16" required /></label>
            <label>默认预算（元 / 餐）<input v-model.number="profileDraft.budget" type="number" min="1" max="9999" required /></label>
            <label>口味偏好<input v-model="profileDraft.taste" maxlength="80" placeholder="例如：清淡、少辣" /></label>
            <label>常用用餐场景<input v-model="profileDraft.dining" maxlength="80" placeholder="例如：学校食堂" /></label>
            <label class="full">忌口或需要避开的食材<input v-model="profileDraft.avoid" maxlength="120" placeholder="例如：花生、虾" /></label>
          </div>
          <p class="profile-hint">收集与你的用餐建议相关的偏好。正式接入后，助手从账号档案读取。</p>
          <button class="button primary" type="submit"><Check :size="17" />保存档案</button>
        </form>
      </div>
    </main>

    <dialog ref="dialog" class="dialog" aria-labelledby="dialog-title" @click.self="dialog?.close()">
      <div class="dialog-head"><h2 id="dialog-title">{{ dialogType === 'log' ? '记录一餐' : '预览分享' }}</h2>
        <button type="button" class="icon-button" aria-label="关闭" @click="dialog?.close()"><X :size="21" /></button>
      </div>
      <form v-if="dialogType === 'log'" class="dialog-form" @submit.prevent="confirmLog">
        <div class="field-grid">
          <label class="full">餐食名称<input v-model="logDraft.name" maxlength="60" required placeholder="例如：番茄豆腐饭" /></label>
          <label>用餐日期<input v-model="logDraft.date" type="date" :max="today" required /></label>
          <label>餐别<select v-model="logDraft.type"><option v-for="type in mealTypes" :key="type">{{ type }}</option></select></label>
          <label class="full">实际份量<input v-model="logDraft.portion" maxlength="140" required placeholder="例如：半碗杂粮饭、1 份豆腐" /></label>
          <label class="full">能量（kcal，可选）<input v-model.number="logDraft.energy" type="number" min="0" max="10000" placeholder="知道数值时再填" /></label>
        </div>
        <button class="button primary" type="submit"><Check :size="17" />确认打卡</button>
      </form>
      <form v-else class="dialog-form" @submit.prevent="confirmShare">
        <label>要分享的餐食<select v-model="shareDraft.logId" required><option v-for="log in sortedLogs.filter(entry => !entry.id.startsWith('demo-'))" :key="log.id" :value="log.id">{{ log.name }} · {{ displayDate(log.date) }}</option></select></label>
        <label>分享内容<textarea v-model="shareDraft.text" maxlength="180" rows="3" placeholder="这餐有什么想分享的？"></textarea></label>
        <div v-if="sharedLog" class="share-preview"><strong>{{ sharedLog.name }}</strong><p>{{ shareDraft.text.trim() || '分享了今天的一餐。' }}</p></div>
        <button class="button primary" type="submit">发布分享</button>
      </form>
    </dialog>
    <Transition><div v-if="toast" class="toast" role="status"><CircleCheck :size="18" />{{ toast }}</div></Transition>
  </div>
</template>
