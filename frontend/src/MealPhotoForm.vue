<script setup>
import { onUnmounted, ref, shallowRef } from 'vue'
import { Camera, Check, ImageUp, LoaderCircle, RotateCcw, Sparkles } from '@lucide/vue'
import { analyzeMeal, formatNutrient, loadExampleAnalysis, nutrientLabels, photoAccept, preparePhoto } from './photos'

defineProps({ saving: Boolean })
const emit = defineEmits(['save'])
const photo = shallowRef(null)
const preview = ref('')
const result = shallowRef(null)
const error = ref('')
const mealHint = ref('')
const isExample = ref(false)
const busy = ref(false)
let request
const estimateLabels = {
  needs_confirmation: '菜名待确认',
  missing_reference: '暂无匹配的营养资料',
  missing_portion: '份量待确认',
}

function setPhoto(blob) {
  if (preview.value) URL.revokeObjectURL(preview.value)
  photo.value = blob
  preview.value = blob ? URL.createObjectURL(blob) : ''
}

function beginRequest() {
  request?.abort()
  request = new AbortController()
  result.value = null
  error.value = ''
  isExample.value = false
  busy.value = true
  return request
}

async function runAnalysis(blob, run) {
  run.signal.throwIfAborted()
  const timeoutSignal = AbortSignal.timeout(80000)
  try {
    const data = await analyzeMeal(blob, AbortSignal.any([run.signal, timeoutSignal]), mealHint.value.trim())
    if (!run.signal.aborted) result.value = data
  } catch (failure) {
    if (!run.signal.aborted) {
      error.value = timeoutSignal.aborted ? '分析超时，请重试。' : failure.message
    }
  }
}

async function useUpload(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  mealHint.value = ''
  const run = beginRequest()
  setPhoto(null)
  try {
    const blob = await preparePhoto(file)
    if (run.signal.aborted) return
    setPhoto(blob)
    await runAnalysis(blob, run)
  } catch (failure) {
    if (!run.signal.aborted) error.value = failure.message
  } finally {
    if (!run.signal.aborted) busy.value = false
  }
}

async function retry() {
  if (!photo.value) return
  const run = beginRequest()
  try {
    await runAnalysis(photo.value, run)
  } finally {
    if (!run.signal.aborted) busy.value = false
  }
}

function submitHint(event) {
  if (event.isComposing || event.keyCode === 229) return
  event.preventDefault()
  retry()
}

async function useExample() {
  const run = beginRequest()
  setPhoto(null)
  try {
    const sample = await loadExampleAnalysis()
    if (run.signal.aborted) return
    setPhoto(sample.photo)
    result.value = sample.analysis
    isExample.value = true
  } catch (failure) {
    if (!run.signal.aborted) error.value = failure.message
  } finally {
    if (!run.signal.aborted) busy.value = false
  }
}

onUnmounted(() => {
  request?.abort()
  if (preview.value) URL.revokeObjectURL(preview.value)
})

function confirm() {
  if (result.value && photo.value && !busy.value) {
    emit('save', { photo: photo.value, analysis: result.value, isExample: isExample.value })
  }
}
</script>

<template>
  <form class="dialog-form photo-form" @submit.prevent="confirm">
    <p class="photo-intro">选一张餐食照片，自动识别你吃了什么并估算营养。</p>

    <div v-if="preview" class="upload-preview">
      <img :src="preview" alt="待打卡的餐食照片" />
    </div>
    <label class="photo-upload" :class="{ compact: preview }">
      <input type="file" :accept="photoAccept" :disabled="saving" @change="useUpload" />
      <Camera :size="preview ? 18 : 28" aria-hidden="true" />
      <strong>{{ preview ? '更换照片' : '选择餐食照片' }}</strong>
      <span v-if="!preview">JPG、PNG 或 WebP · 最大 15 MB</span>
    </label>
    <p v-if="!preview" class="photo-note">你选择的照片会上传至后端，由 DeepSeek 官方 API 分析。</p>
    <button v-if="!busy && !result" class="button quiet photo-example" type="button" :disabled="saving" @click="useExample">
      <ImageUp :size="17" />试用示例照片
    </button>

    <p v-if="busy" class="photo-status" role="status"><LoaderCircle :size="18" class="spin" />正在识别食物并核对营养资料…</p>
    <div v-if="error" class="photo-error" role="alert">
      <p>{{ error }}</p>
    </div>

    <section v-if="result" class="analysis" aria-label="照片分析结果">
      <div class="analysis-heading">
        <span><Sparkles :size="17" />{{ isExample ? '示例分析' : 'AI 估算结果' }}</span>
        <small>份量与营养为估算</small>
      </div>
      <dl class="nutrient-grid">
        <div v-for="(metric, key) in nutrientLabels" :key="key">
          <dt>{{ metric.label }}</dt>
          <dd>{{ formatNutrient(result.totals[key]) }} <small v-if="result.totals[key] != null">{{ metric.unit }}</small></dd>
        </div>
      </dl>
      <ul class="analysis-foods">
        <li v-for="(food, index) in result.foods" :key="index">
          <strong>{{ food.name }}</strong><span>{{ food.category }}</span>
          <small>{{ food.estimated_grams != null ? `约 ${formatNutrient(food.estimated_grams)} g` : food.portion || '份量未知' }}</small>
          <div v-if="food.reference || estimateLabels[food.status]" class="analysis-evidence">
            <span v-if="food.energy_kcal != null">约 {{ formatNutrient(food.energy_kcal) }} kcal</span>
            <span v-if="estimateLabels[food.status]">{{ estimateLabels[food.status] }}</span>
            <a v-if="food.reference" :href="food.reference.url" target="_blank" rel="noreferrer">
              {{ food.reference.label || 'USDA' }} · {{ food.reference.name }}
            </a>
            <p v-if="food.reference?.basis === 'per_serving'" class="analysis-reference-serving">
              <strong>参考配方每份</strong>
              <span v-for="(metric, key) in nutrientLabels" :key="key">
                {{ metric.label }} {{ formatNutrient(food.reference.nutrients[key]) }} {{ metric.unit }}
              </span>
            </p>
          </div>
        </li>
      </ul>
      <p v-if="result.follow_up" class="photo-question">{{ result.follow_up }}</p>
      <p v-if="result.notes && result.notes !== result.follow_up" class="photo-note">{{ result.notes }}</p>
      <p v-if="result.foods.some(food => estimateLabels[food.status])" class="photo-note">部分食物还无法换算。你可以先保存食物记录，整餐营养会标为未知。</p>
      <p v-if="result.foods.some(food => food.status === 'recipe_reference')" class="photo-note">参考配方的每份用料和份量可能不同。你的实际营养摄入会标为未知。</p>
    </section>

    <div v-if="preview && !isExample && !busy && (result || error)" class="photo-refinement">
      <label>
        补充菜名、做法或实际吃的量（选填）
        <input v-model="mealHint" type="text" maxlength="240" :disabled="saving"
          placeholder="例如：水煮鸡蛋 1 个，白米饭吃了约 120 克" @keydown.enter="submitHint" />
      </label>
      <button class="button quiet" type="button" :disabled="saving" @click="retry"><RotateCcw :size="14" />重新分析</button>
    </div>

    <button class="button primary" type="submit" :disabled="!result || busy || saving"><Check :size="17" />{{ saving ? '正在保存…' : '确认打卡' }}</button>
  </form>
</template>

