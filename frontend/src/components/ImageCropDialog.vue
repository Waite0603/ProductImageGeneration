<script setup>
import { computed, nextTick, onBeforeUnmount, reactive, ref, watch } from 'vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  sourceUrl: { type: String, default: '' },
  /** Max output width in px; height follows crop aspect */
  outputWidth: { type: Number, default: 1040 },
})

const emit = defineEmits(['close', 'confirm'])

const PRESETS = [
  { id: '16:9', label: '16:9', w: 16, h: 9 },
  { id: '4:3', label: '4:3', w: 4, h: 3 },
  { id: '1:1', label: '1:1', w: 1, h: 1 },
  { id: '3:4', label: '3:4', w: 3, h: 4 },
  { id: '9:16', label: '9:16', w: 9, h: 16 },
  { id: 'free', label: '自由', w: 0, h: 0 },
]

const stageRef = ref(null)
const imgRef = ref(null)
const ready = ref(false)
const ratioMode = ref('16:9')
const customW = ref(16)
const customH = ref(9)

const imgNatural = reactive({ w: 0, h: 0 })
const draw = reactive({ x: 0, y: 0, w: 0, h: 0 })
const crop = reactive({ x: 0, y: 0, w: 0, h: 0 })

let drag = null

const isFree = computed(() => ratioMode.value === 'free')

const aspect = computed(() => {
  if (isFree.value) return null
  if (ratioMode.value === 'custom') {
    const w = Math.max(1, Number(customW.value) || 1)
    const h = Math.max(1, Number(customH.value) || 1)
    return w / h
  }
  const preset = PRESETS.find((p) => p.id === ratioMode.value)
  return preset ? preset.w / preset.h : 16 / 9
})

const outputHeight = computed(() => {
  if (isFree.value) {
    const ratio = crop.w > 0 ? crop.h / crop.w : 1
    return Math.max(1, Math.round(props.outputWidth * ratio))
  }
  return Math.round(props.outputWidth / aspect.value)
})

const ratioLabel = computed(() => {
  if (isFree.value) return '自由比例'
  if (ratioMode.value === 'custom') return `${customW.value}:${customH.value}`
  return ratioMode.value
})

function fitCropToAspect() {
  if (!draw.w || !draw.h) return

  if (isFree.value) {
    crop.w = draw.w * 0.85
    crop.h = draw.h * 0.85
    crop.x = draw.x + (draw.w - crop.w) / 2
    crop.y = draw.y + (draw.h - crop.h) / 2
    clampCrop()
    return
  }

  const ar = aspect.value
  let cw = draw.w
  let ch = cw / ar
  if (ch > draw.h) {
    ch = draw.h
    cw = ch * ar
  }
  crop.w = cw
  crop.h = ch
  crop.x = draw.x + (draw.w - cw) / 2
  crop.y = draw.y + (draw.h - ch) / 2
  clampCrop()
}

function layout() {
  const stage = stageRef.value
  const img = imgRef.value
  if (!stage || !img || !imgNatural.w) return

  const sw = stage.clientWidth
  const sh = stage.clientHeight
  const scale = Math.min(sw / imgNatural.w, sh / imgNatural.h)
  draw.w = imgNatural.w * scale
  draw.h = imgNatural.h * scale
  draw.x = (sw - draw.w) / 2
  draw.y = (sh - draw.h) / 2

  fitCropToAspect()
  ready.value = true
}

function onImageLoad() {
  const img = imgRef.value
  if (!img) return
  imgNatural.w = img.naturalWidth
  imgNatural.h = img.naturalHeight
  nextTick(layout)
}

function clampCrop() {
  crop.w = Math.max(40, Math.min(crop.w, draw.w))
  crop.h = Math.max(40, Math.min(crop.h, draw.h))

  if (!isFree.value) {
    const ar = aspect.value
    if (crop.w / crop.h > ar) crop.w = crop.h * ar
    else crop.h = crop.w / ar
  }

  crop.x = Math.min(Math.max(crop.x, draw.x), draw.x + draw.w - crop.w)
  crop.y = Math.min(Math.max(crop.y, draw.y), draw.y + draw.h - crop.h)
}

function startMove(e) {
  if (!ready.value) return
  e.preventDefault()
  const point = e.touches ? e.touches[0] : e
  drag = {
    type: 'move',
    sx: point.clientX,
    sy: point.clientY,
    ox: crop.x,
    oy: crop.y,
  }
  bindPointer()
}

function startResize(e) {
  if (!ready.value) return
  e.preventDefault()
  e.stopPropagation()
  const point = e.touches ? e.touches[0] : e
  drag = {
    type: 'resize',
    sx: point.clientX,
    sy: point.clientY,
    ow: crop.w,
    oh: crop.h,
    ox: crop.x,
    oy: crop.y,
  }
  bindPointer()
}

function bindPointer() {
  window.addEventListener('mousemove', onPointerMove)
  window.addEventListener('mouseup', endPointer)
  window.addEventListener('touchmove', onPointerMove, { passive: false })
  window.addEventListener('touchend', endPointer)
}

function onPointerMove(e) {
  if (!drag) return
  e.preventDefault?.()
  const point = e.touches ? e.touches[0] : e
  const dx = point.clientX - drag.sx
  const dy = point.clientY - drag.sy

  if (drag.type === 'move') {
    crop.x = drag.ox + dx
    crop.y = drag.oy + dy
    clampCrop()
    return
  }

  if (isFree.value) {
    crop.w = Math.max(40, drag.ow + dx)
    crop.h = Math.max(40, drag.oh + dy)
    crop.x = drag.ox
    crop.y = drag.oy
    clampCrop()
    return
  }

  const nextW = Math.max(40, drag.ow + dx)
  crop.w = nextW
  crop.h = nextW / aspect.value
  crop.x = drag.ox
  crop.y = drag.oy
  clampCrop()
}

function endPointer() {
  drag = null
  window.removeEventListener('mousemove', onPointerMove)
  window.removeEventListener('mouseup', endPointer)
  window.removeEventListener('touchmove', onPointerMove)
  window.removeEventListener('touchend', endPointer)
}

function selectPreset(id) {
  ratioMode.value = id
  if (ready.value) fitCropToAspect()
}

function applyCustomRatio() {
  ratioMode.value = 'custom'
  if (ready.value) fitCropToAspect()
}

function confirmCrop() {
  const img = imgRef.value
  if (!img || !ready.value) return

  const scaleX = imgNatural.w / draw.w
  const scaleY = imgNatural.h / draw.h
  const sx = (crop.x - draw.x) * scaleX
  const sy = (crop.y - draw.y) * scaleY
  const sw = crop.w * scaleX
  const sh = crop.h * scaleY

  const outW = props.outputWidth
  const outH = isFree.value
    ? Math.max(1, Math.round(outW * (crop.h / crop.w)))
    : outputHeight.value

  const canvas = document.createElement('canvas')
  canvas.width = outW
  canvas.height = outH
  const ctx = canvas.getContext('2d')
  ctx.imageSmoothingEnabled = true
  ctx.imageSmoothingQuality = 'high'
  ctx.fillStyle = '#ffffff'
  ctx.fillRect(0, 0, canvas.width, canvas.height)
  ctx.drawImage(img, sx, sy, sw, sh, 0, 0, outW, outH)

  emit('confirm', canvas.toDataURL('image/jpeg', 0.92))
}

function close() {
  emit('close')
}

watch(
  () => [props.open, props.sourceUrl],
  async ([open]) => {
    ready.value = false
    window.removeEventListener('resize', layout)
    if (!open) return
    ratioMode.value = '16:9'
    customW.value = 16
    customH.value = 9
    await nextTick()
    if (imgRef.value?.complete && imgRef.value.naturalWidth) onImageLoad()
    window.addEventListener('resize', layout)
  },
)

onBeforeUnmount(() => {
  endPointer()
  window.removeEventListener('resize', layout)
})
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="crop-mask" @click.self="close">
      <div class="crop-dialog" role="dialog" aria-modal="true">
        <header class="crop-header">
          <div>
            <p class="crop-kicker">IMAGE CROP</p>
            <h3>裁剪图片</h3>
            <p>
              拖动选区移动，右下角拉伸 · 比例 {{ ratioLabel }} · 输出约
              {{ outputWidth }}×{{ outputHeight }}
            </p>
          </div>
          <button type="button" class="crop-x" aria-label="关闭" @click="close">关闭</button>
        </header>

        <div class="ratio-bar">
          <button
            v-for="item in PRESETS"
            :key="item.id"
            type="button"
            class="ratio-btn"
            :class="{ active: ratioMode === item.id }"
            @click="selectPreset(item.id)"
          >
            {{ item.label }}
          </button>
          <div class="ratio-custom" :class="{ active: ratioMode === 'custom' }">
            <input
              v-model.number="customW"
              type="number"
              min="1"
              max="99"
              aria-label="宽比例"
              @keydown.enter="applyCustomRatio"
            />
            <span>:</span>
            <input
              v-model.number="customH"
              type="number"
              min="1"
              max="99"
              aria-label="高比例"
              @keydown.enter="applyCustomRatio"
            />
            <button type="button" class="ratio-apply" @click="applyCustomRatio">
              自定义
            </button>
          </div>
        </div>

        <div ref="stageRef" class="crop-stage">
          <img
            v-if="sourceUrl"
            ref="imgRef"
            class="crop-source"
            :src="sourceUrl"
            alt="待裁剪"
            draggable="false"
            :style="
              ready
                ? {
                    left: draw.x + 'px',
                    top: draw.y + 'px',
                    width: draw.w + 'px',
                    height: draw.h + 'px',
                    opacity: 1,
                  }
                : { opacity: 0 }
            "
            @load="onImageLoad"
          />

          <div
            v-if="ready"
            class="crop-box"
            :style="{
              left: crop.x + 'px',
              top: crop.y + 'px',
              width: crop.w + 'px',
              height: crop.h + 'px',
            }"
            @mousedown="startMove"
            @touchstart="startMove"
          >
            <span class="crop-grid" />
            <i
              class="crop-handle"
              @mousedown="startResize"
              @touchstart="startResize"
            />
          </div>
        </div>

        <footer class="crop-footer">
          <button type="button" class="btn ghost" @click="close">取消</button>
          <button type="button" class="btn primary" :disabled="!ready" @click="confirmCrop">
            确认裁剪
          </button>
        </footer>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.crop-mask {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(28, 22, 16, 0.5);
  backdrop-filter: blur(8px);
  box-sizing: border-box;
}

.crop-dialog {
  width: min(920px, 100%);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.7), rgba(255, 255, 255, 0.32)),
    #f7f4ef;
  border-radius: 22px;
  border: 1px solid rgba(255, 255, 255, 0.7);
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.8) inset,
    0 28px 70px rgba(20, 16, 12, 0.28);
  overflow: hidden;
}

.crop-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 20px 22px 10px;
}

.crop-kicker {
  margin: 0 0 4px;
  font-size: 10px;
  letter-spacing: 0.16em;
  color: #8a857e;
  font-weight: 700;
}

.crop-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 800;
  color: #1a1a1a;
}

.crop-header p {
  margin: 6px 0 0;
  font-size: 12px;
  line-height: 1.55;
  color: #8a857e;
}

.crop-x {
  appearance: none;
  flex-shrink: 0;
  border: 1px solid #ddd4c8;
  background: #fff;
  color: #1a1a1a;
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.crop-x:hover {
  border-color: #c45c4a;
  color: #c45c4a;
}

.ratio-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 0 22px 14px;
}

.ratio-btn {
  appearance: none;
  border: 1px solid #d8d0c4;
  background: #fff;
  color: #1a1a1a;
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.ratio-btn.active {
  border-color: #c45c4a;
  background: #c45c4a;
  color: #fff;
}

.ratio-custom {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: 999px;
  border: 1px solid #d8d0c4;
  background: #fff;
}

.ratio-custom.active {
  border-color: #c45c4a;
  box-shadow: 0 0 0 1px rgba(196, 92, 74, 0.15);
}

.ratio-custom input {
  width: 42px;
  border: none;
  background: transparent;
  font-size: 12px;
  font-weight: 700;
  text-align: center;
  color: #1a1a1a;
  outline: none;
}

.ratio-custom span {
  font-size: 12px;
  color: #8a857e;
}

.ratio-apply {
  appearance: none;
  border: none;
  background: #ebe6df;
  color: #1a1a1a;
  border-radius: 999px;
  padding: 4px 8px;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
}

.crop-stage {
  position: relative;
  height: min(58vh, 480px);
  margin: 0 22px;
  background: #1f1f1f;
  border-radius: 12px;
  overflow: hidden;
  user-select: none;
  touch-action: none;
}

.crop-source {
  position: absolute;
  display: block;
  max-width: none;
  pointer-events: none;
  user-select: none;
}

.crop-box {
  position: absolute;
  box-sizing: border-box;
  border: 2px solid #fff;
  box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.45);
  cursor: move;
}

.crop-grid {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(to right, transparent 33.33%, rgba(255, 255, 255, 0.35) 33.33%, rgba(255, 255, 255, 0.35) 33.66%, transparent 33.66%, transparent 66.33%, rgba(255, 255, 255, 0.35) 66.33%, rgba(255, 255, 255, 0.35) 66.66%, transparent 66.66%),
    linear-gradient(to bottom, transparent 33.33%, rgba(255, 255, 255, 0.35) 33.33%, rgba(255, 255, 255, 0.35) 33.66%, transparent 33.66%, transparent 66.33%, rgba(255, 255, 255, 0.35) 66.33%, rgba(255, 255, 255, 0.35) 66.66%, transparent 66.66%);
  pointer-events: none;
}

.crop-handle {
  position: absolute;
  right: -7px;
  bottom: -7px;
  width: 16px;
  height: 16px;
  border-radius: 3px;
  background: #c45c4a;
  border: 2px solid #fff;
  cursor: nwse-resize;
  box-sizing: border-box;
}

.crop-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 16px 22px 18px;
}

.btn {
  appearance: none;
  border: none;
  border-radius: 999px;
  padding: 10px 18px;
  min-width: 88px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn.ghost {
  background: #efeae3;
  color: #1a1a1a;
}

.btn.ghost:hover {
  background: #e7e0d6;
}

.btn.primary {
  background: #1f1f1f;
  color: #fff;
}

.btn.primary:hover:not(:disabled) {
  background: #333;
}
</style>
