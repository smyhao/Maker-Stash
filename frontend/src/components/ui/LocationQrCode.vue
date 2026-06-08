<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import QRCode from 'qrcode'

const props = withDefaults(defineProps<{
  value: string
  size?: number
}>(), {
  size: 132,
})

const dataUrl = ref('')

async function render() {
  dataUrl.value = await QRCode.toDataURL(props.value, {
    errorCorrectionLevel: 'M',
    margin: 1,
    width: props.size,
  })
}

onMounted(render)
watch(() => [props.value, props.size], render)
</script>

<template>
  <img v-if="dataUrl" :src="dataUrl" :alt="value" class="block" :width="size" :height="size" />
  <div v-else class="grid place-items-center bg-wash text-[12px] text-muted" :style="{ width: `${size}px`, height: `${size}px` }">QR</div>
</template>
