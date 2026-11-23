<script setup>
import { ref, watch } from 'vue'
import { getPhoto } from './photos'

const props = defineProps({
  photoId: { type: String, required: true },
  alt: { type: String, default: '餐食照片' },
})
const source = ref('')

watch(() => props.photoId, async (id, _, cleanup) => {
  let stale = false
  let url
  source.value = ''
  cleanup(() => {
    stale = true
    if (url) URL.revokeObjectURL(url)
  })
  if (!id) return
  try {
    const photo = await getPhoto(id)
    if (stale || !photo) return
    url = URL.createObjectURL(photo)
    source.value = url
  } catch {
    // A missing local image still leaves the text of a record or post readable.
  }
}, { immediate: true })
</script>

<template>
  <img v-if="source" :src="source" :alt="alt" loading="lazy" />
</template>

