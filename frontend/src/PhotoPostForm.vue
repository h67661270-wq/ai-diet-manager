<script setup>
import { computed, onUnmounted, ref, shallowRef } from 'vue'
import { ImageUp, X } from '@lucide/vue'
import StoredPhoto from './StoredPhoto.vue'
import { photoAccept, preparePhoto } from './photos'

const props = defineProps({ initialLog: Object, saving: Boolean, communityOnline: Boolean })
const emit = defineEmits(['publish'])
const title = ref(props.initialLog?.name?.slice(0, 60) ?? '')
const text = ref('')
const photo = shallowRef(null)
const photoId = ref(props.initialLog?.photoId ?? '')
const preview = ref('')
const busy = ref(false)
const error = ref('')
let selection = 0

const canPublish = computed(() => title.value.trim() && (text.value.trim() || photo.value || photoId.value))

function clearPhoto() {
  selection += 1
  if (preview.value) URL.revokeObjectURL(preview.value)
  preview.value = ''
  photoId.value = ''
  photo.value = null
  busy.value = false
  error.value = ''
}

async function useImage(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  const revision = ++selection
  busy.value = true
  error.value = ''
  try {
    const blob = await preparePhoto(file)
    if (revision !== selection) return
    if (preview.value) URL.revokeObjectURL(preview.value)
    photoId.value = ''
    photo.value = blob
    preview.value = URL.createObjectURL(blob)
  } catch (failure) {
    if (revision === selection) error.value = failure.message
  } finally {
    if (revision === selection) busy.value = false
  }
}

function publish() {
  if (!canPublish.value || busy.value || props.saving) return
  emit('publish', { title: title.value.trim(), text: text.value.trim(), photo: photo.value, photoId: photoId.value })
}

onUnmounted(clearPhoto)
</script>

<template>
  <form class="dialog-form photo-post-form" @submit.prevent="publish">
    <p class="photo-note">{{ communityOnline ? '帖子和配图发布后，访问同一社区的人都能看到。' : '当前为本地社区，帖子保存在这个浏览器。' }}</p>
    <label>帖子标题<input v-model="title" maxlength="60" required placeholder="给这餐起个标题" /></label>
    <label>分享内容<textarea v-model="text" maxlength="400" rows="4" placeholder="写下你的用餐心得…"></textarea></label>
    <div v-if="preview || photoId" class="upload-preview post-upload-preview">
      <img v-if="preview" :src="preview" alt="帖子配图预览" />
      <StoredPhoto v-else :photo-id="photoId" alt="来自饮食打卡的照片" />
      <button class="icon-button remove-photo" type="button" aria-label="移除配图" :disabled="saving" @click="clearPhoto"><X :size="17" /></button>
    </div>
    <label class="photo-upload compact">
      <input type="file" :accept="photoAccept" :disabled="saving" @change="useImage" />
      <ImageUp :size="19" aria-hidden="true" />
      <strong>{{ preview || photoId ? '更换配图' : '添加配图' }}</strong>
    </label>
    <p v-if="busy" class="photo-note" role="status">正在处理图片…</p>
    <p v-if="error" class="form-error" role="alert">{{ error }}</p>
    <button class="button primary" type="submit" :disabled="!canPublish || busy || saving">{{ saving ? '正在发布…' : '发布帖子' }}</button>
  </form>
</template>

