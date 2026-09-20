<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import yellow from '../assets/shoes/yellow.png'
import ImageCropDialog from './ImageCropDialog.vue'
import AppModal from './AppModal.vue'
import { DEFAULT_THEME_ID, THEME_MAP, resolveThemeId } from '../themes'

/** Display max ~520px; export uses 2x for sharpness */
const HERO_OUTPUT_WIDTH = 1040

const props = defineProps({
  activeId: {
    type: String,
    default: 'yellow',
  },
  editing: {
    type: Boolean,
    default: false,
  },
  themeId: {
    type: String,
    default: DEFAULT_THEME_ID,
  },
})

const emit = defineEmits(['update:activeId', 'update:themeId', 'change'])

const resolvedThemeId = computed(() => resolveThemeId(props.themeId))

let idSeq = 0
function createId(prefix = 'color') {
  idSeq += 1
  return `${prefix}-${Date.now()}-${idSeq}`
}

function clone(value) {
  return JSON.parse(JSON.stringify(value))
}

const DEFAULT_VARIANTS = [
  { id: 'yellow', name: '姜黄', accent: '#C9A227', image: yellow },
]

/** Editable thumbnail list — main image follows active tab */
const variants = ref(DEFAULT_VARIANTS.map((item) => ({ ...item })))

const active = computed(
  () => variants.value.find((v) => v.id === props.activeId) ?? variants.value[0],
)

const content = reactive({
  priceLabel: '直播价 LIVE PRICE',
  priceValue: '¥287',
  featureChip: '隐形增高 · 舒适不累脚',
  brandZh: '范小洛',
  brandEn: 'FAN XIAO LUO',
  styleLabel: '款号 STYLE NO.',
  styleNo: '2669',
  title: '内增高德训鞋 · 隐形增高7CM',
  subtitle: '头层牛反绒 · 猪皮乳胶鞋垫 · 橡胶防滑底',
  specsTitle: '产品参数 · SPECS',
  specs: [
    { id: 's1', label: '码数 SIZE', value: '34-40码' },
    { id: 's2', label: '鞋面 UPPER', value: '头层牛反绒' },
    { id: 's3', label: '内里 LINING', value: '超纤皮' },
    { id: 's4', label: '鞋垫 INSOLE', value: '猪皮乳胶垫' },
    { id: 's5', label: '鞋底 OUTSOLE', value: '橡胶防滑底' },
    { id: 's6', label: '跟高 HEEL', value: '4CM + 内增高3CM' },
  ],
  formulaTitle: '科学增高设计',
  formulaLine1: '外露鞋跟 4CM + 隐形内增高垫 3CM',
  formulaLine2: '总增高约 7CM · 外观自然不突兀',
  showFormulaBlock: true,
  showFormulaMath: true,
  stageBg: '#ffffff',
  thumbBg: '#ffffff',
  formulaNums: [
    { num: '4', label: 'CM 外跟' },
    { num: '3', label: 'CM 内增' },
    { num: '7', label: 'CM 总增高' },
  ],
  /** Per-field font size overrides (px), keyed by data-sync */
  fontSizes: {},
})

const DEFAULT_CONTENT = clone(content)

const DEFAULT_FONT_SIZES = {
  priceLabel: 10,
  priceValue: 30,
  featureChip: 12,
  brandZh: 34,
  brandEn: 12,
  styleLabel: 11,
  styleNo: 25,
  title: 24,
  subtitle: 13,
  specsTitle: 13,
  formulaTitle: 15,
  formulaLine1: 11,
  formulaLine2: 11,
}

const FONT_SIZE_MIN = 8
const FONT_SIZE_MAX = 72

const activeSyncKey = ref('')

function defaultFontSize(key) {
  if (key.startsWith('spec.')) return key.endsWith('.label') ? 11 : 14
  if (key.startsWith('formulaNum.')) return key.endsWith('.num') ? 24 : 9
  return DEFAULT_FONT_SIZES[key] ?? 14
}

function queryBySync(key) {
  if (!key || !boardEl.value) return null
  return boardEl.value.querySelector(`[data-sync="${key}"]`)
}

function resolveFontSize(key) {
  if (content.fontSizes[key] != null) return content.fontSizes[key]
  const el = queryBySync(key)
  if (el instanceof HTMLElement) {
    const px = parseFloat(getComputedStyle(el).fontSize)
    if (px) return Math.round(px)
  }
  return defaultFontSize(key)
}

const fontSizeDraft = ref(14)
const fontSizeInputFocused = ref(false)

function syncFontSizeDraft() {
  if (!activeSyncKey.value) return
  fontSizeDraft.value = resolveFontSize(activeSyncKey.value)
}

function fontStyle(key) {
  const px = content.fontSizes[key]
  if (px == null) return undefined
  return { fontSize: `${px}px` }
}

function setFontSize(key, px) {
  const next = Math.min(FONT_SIZE_MAX, Math.max(FONT_SIZE_MIN, Math.round(px)))
  content.fontSizes[key] = next
}

function adjustFontSize(delta) {
  const key = activeSyncKey.value
  if (!key) return
  setFontSize(key, resolveFontSize(key) + delta)
  fontSizeDraft.value = content.fontSizes[key]
}

function onFontSizeFocus() {
  fontSizeInputFocused.value = true
  syncFontSizeDraft()
}

function commitFontSizeDraft() {
  fontSizeInputFocused.value = false
  const key = activeSyncKey.value
  if (!key) return
  const val = Number(fontSizeDraft.value)
  if (Number.isFinite(val)) {
    setFontSize(key, val)
    fontSizeDraft.value = content.fontSizes[key]
  } else {
    syncFontSizeDraft()
  }
}

function onFontSizeKeydown(e) {
  if (e.key === 'Enter') {
    e.preventDefault()
    commitFontSizeDraft()
    e.currentTarget.blur()
  }
}

function resetActiveFontSize() {
  const key = activeSyncKey.value
  if (!key) return
  delete content.fontSizes[key]
}

function onBoardInput(e) {
  const t = e.target
  if (!(t instanceof HTMLElement) || !t.isContentEditable || !t.dataset.sync) return
  emit('change')
}

function onBoardFocusIn(e) {
  if (!props.editing) return
  const t = e.target
  if (t instanceof HTMLElement && t.isContentEditable && t.dataset.sync) {
    activeSyncKey.value = t.dataset.sync
  }
}

watch(activeSyncKey, (key) => {
  if (key && !fontSizeInputFocused.value) syncFontSizeDraft()
})

watch(
  () => props.editing,
  (on) => {
    if (!on) {
      activeSyncKey.value = ''
      fontSizeInputFocused.value = false
    }
  },
)

const boardStyle = computed(() => ({
  '--accent': active.value?.accent || '#C9A227',
  '--stage-bg': content.stageBg,
  '--thumb-bg': content.thumbBg,
}))

const cropOpen = ref(false)
const cropSource = ref('')
const cropTargetId = ref('')
/** 'replace' | 'add' */
const cropMode = ref('replace')
const fileInputRef = ref(null)
const boardEl = ref(null)
const infoOverflow = ref(false)
let overflowRaf = 0
let overflowRo = null
let overflowMo = null

function measureBottomOverflow() {
  const board = boardEl.value
  if (!board) {
    infoOverflow.value = false
    return
  }

  const boardRect = board.getBoundingClientRect()
  // overflow:hidden clips at the border box, not the padding box
  const limitBottom = boardRect.bottom
  const limitRight = boardRect.right
  const limitLeft = boardRect.left

  const targets = [
    board.querySelector('.formula'),
    board.querySelector('.formula-block-restore'),
    board.querySelector('.thumbs'),
  ].filter((el) => el instanceof HTMLElement)

  infoOverflow.value = targets.some((el) => {
    const r = el.getBoundingClientRect()
    return r.bottom > limitBottom + 1.5 || r.right > limitRight + 1.5 || r.left < limitLeft - 1.5
  })
}

function scheduleOverflowCheck() {
  if (overflowRaf) cancelAnimationFrame(overflowRaf)
  overflowRaf = requestAnimationFrame(() => {
    overflowRaf = 0
    measureBottomOverflow()
  })
}

onMounted(() => {
  const board = boardEl.value
  if (!board) return

  overflowRo = new ResizeObserver(() => scheduleOverflowCheck())
  overflowRo.observe(board)

  overflowMo = new MutationObserver(() => scheduleOverflowCheck())
  overflowMo.observe(board, {
    subtree: true,
    childList: true,
    characterData: true,
  })

  nextTick(scheduleOverflowCheck)
})

onBeforeUnmount(() => {
  if (overflowRaf) cancelAnimationFrame(overflowRaf)
  overflowRo?.disconnect()
  overflowMo?.disconnect()
})

watch(
  () => [props.editing, props.themeId, content.showFormulaBlock, content.showFormulaMath, content.fontSizes],
  () => nextTick(scheduleOverflowCheck),
  { deep: true },
)

function selectVariant(id) {
  emit('update:activeId', id)
}

function readPlainText(el) {
  return (el.innerText || '').replace(/\u00a0/g, ' ').replace(/\r/g, '').trimEnd()
}

function syncText(e, setter) {
  setter(readPlainText(e.target))
}

function applySyncKey(key, text, target = content) {
  if (!key) return
  if (key.startsWith('spec.')) {
    const [, specId, field] = key.split('.')
    const spec = target.specs?.find((item) => item.id === specId)
    if (spec && (field === 'label' || field === 'value')) {
      if (text) spec[field] = text
    }
    return
  }
  if (key.startsWith('formulaNum.')) {
    const [, index, field] = key.split('.')
    const item = target.formulaNums?.[Number(index)]
    if (item && (field === 'num' || field === 'label')) {
      if (text) item[field] = text
    }
    return
  }
  if (Object.prototype.hasOwnProperty.call(target, key)) {
    if (text) target[key] = text
  }
}

function overlayDomText(target) {
  const root = boardEl.value
  if (!root) return
  root.querySelectorAll('[data-sync]').forEach((node) => {
    if (!(node instanceof HTMLElement)) return
    applySyncKey(node.dataset.sync, readPlainText(node), target)
  })
}

/** Flush DOM edits before leaving edit mode (even if focus not blurred yet) */
function flushEditableContent(blurActive = true) {
  const root = boardEl.value
  if (!root) return

  const ae = document.activeElement
  if (ae instanceof HTMLElement && root.contains(ae) && ae.isContentEditable) {
    applySyncKey(ae.dataset.sync, readPlainText(ae))
    if (blurActive) ae.blur()
  }

  overlayDomText(content)
}

function getSnapshot() {
  const data = clone({
    activeId: props.activeId,
    themeId: resolvedThemeId.value,
    variants: variants.value,
    content,
  })
  overlayDomText(data.content)
  return data
}

function adoptTheme(fromId, toId) {
  const next = THEME_MAP[resolveThemeId(toId)]
  if (!next) return
  const prev = THEME_MAP[fromId]
  if (!prev || content.stageBg === prev.stageBg) content.stageBg = next.stageBg
  if (!prev || content.thumbBg === prev.thumbBg) content.thumbBg = next.thumbBg
}

function resetToDefault() {
  applySnapshot({
    activeId: 'yellow',
    themeId: DEFAULT_THEME_ID,
    variants: DEFAULT_VARIANTS.map((item) => ({ ...item })),
    content: clone(DEFAULT_CONTENT),
  })
}

let applyingSnapshot = false

function applySnapshot(data) {
  if (!data || typeof data !== 'object') return
  applyingSnapshot = true

  const nextContent = data.content
  if (nextContent && typeof nextContent === 'object') {
    for (const key of Object.keys(content)) {
      if (Object.prototype.hasOwnProperty.call(nextContent, key)) {
        content[key] = nextContent[key]
      }
    }
  }

  if (Array.isArray(data.variants) && data.variants.length) {
    variants.value = data.variants.map((item) => ({ ...item }))
  }

  const nextId = data.activeId
  if (nextId && variants.value.some((item) => item.id === nextId)) {
    emit('update:activeId', nextId)
  } else if (variants.value[0]) {
    emit('update:activeId', variants.value[0].id)
  }

  emit('update:themeId', resolveThemeId(data.themeId))

  nextTick(() => {
    applyingSnapshot = false
    scheduleOverflowCheck()
  })
}

watch(
  () => [props.activeId, props.themeId, variants.value, content],
  () => {
    if (!applyingSnapshot) emit('change')
  },
  { deep: true },
)

defineExpose({ flushEditableContent, getSnapshot, applySnapshot, resetToDefault, adoptTheme })

function placeCaretAfter(node) {
  const sel = window.getSelection()
  if (!sel) return
  const range = document.createRange()
  range.setStartAfter(node)
  range.collapse(true)
  sel.removeAllRanges()
  sel.addRange(range)
}

/** Insert plain text at the caret, keeping line breaks as <br>. */
function insertPlainAtCaret(text) {
  const sel = window.getSelection()
  if (!sel || sel.rangeCount === 0) return

  const range = sel.getRangeAt(0)
  range.deleteContents()

  const normalized = String(text).replace(/\r\n/g, '\n').replace(/\r/g, '\n')
  const lines = normalized.split('\n')
  const frag = document.createDocumentFragment()
  const nodes = []

  lines.forEach((line, i) => {
    if (i > 0) {
      const br = document.createElement('br')
      frag.appendChild(br)
      nodes.push(br)
    }
    if (line) {
      const node = document.createTextNode(line)
      frag.appendChild(node)
      nodes.push(node)
    }
  })

  if (!nodes.length) {
    const br = document.createElement('br')
    frag.appendChild(br)
    nodes.push(br)
  }

  const last = nodes[nodes.length - 1]
  range.insertNode(frag)

  // Trailing <br> is ignored unless followed by another node; keep an extra one
  // so Enter at the end of a field still shows a new empty line.
  if (last.nodeName === 'BR' && last.parentNode && last.parentNode.lastChild === last) {
    last.parentNode.appendChild(document.createElement('br'))
  }

  placeCaretAfter(last)
  scheduleOverflowCheck()
}

function onEditKeydown(e) {
  if (e.key !== 'Enter' || e.isComposing) return
  e.preventDefault()
  insertPlainAtCaret('\n')
}

/** Paste as plain text only — strip copied font/HTML styles, keep newlines */
function onPastePlain(e) {
  const el = e.target
  if (!(el instanceof HTMLElement) || !el.isContentEditable) return
  e.preventDefault()
  const text = e.clipboardData?.getData('text/plain') || ''
  insertPlainAtCaret(text)
}

function openReplaceUpload(variantId) {
  cropMode.value = 'replace'
  cropTargetId.value = variantId
  fileInputRef.value?.click()
}

function openAddUpload() {
  cropMode.value = 'add'
  cropTargetId.value = ''
  fileInputRef.value?.click()
}

function onFilePicked(e) {
  const file = e.target.files?.[0]
  e.target.value = ''
  if (!file || !file.type.startsWith('image/')) return

  const url = URL.createObjectURL(file)
  if (cropSource.value.startsWith('blob:')) URL.revokeObjectURL(cropSource.value)
  cropSource.value = url
  cropOpen.value = true
}

function closeCrop() {
  cropOpen.value = false
  if (cropSource.value.startsWith('blob:')) {
    URL.revokeObjectURL(cropSource.value)
  }
  cropSource.value = ''
  cropTargetId.value = ''
  cropMode.value = 'replace'
}

function onCropConfirm(dataUrl) {
  if (cropMode.value === 'add') {
    const id = createId('color')
    const accents = ['#C9A227', '#A33A3A', '#6B8CAE', '#9898A0', '#C48A92', '#5B8C5A']
    variants.value.push({
      id,
      name: `配色${variants.value.length + 1}`,
      accent: accents[variants.value.length % accents.length],
      image: dataUrl,
    })
    emit('update:activeId', id)
  } else {
    const id = cropTargetId.value
    const item = variants.value.find((v) => v.id === id)
    if (item) {
      item.image = dataUrl
      emit('update:activeId', id)
    }
  }
  closeCrop()
}

function addSpec() {
  content.specs.push({
    id: createId('s'),
    label: '参数名',
    value: '参数值',
  })
  scheduleOverflowCheck()
}

function removeSpec(specId) {
  const idx = content.specs.findIndex((item) => item.id === specId)
  if (idx < 0) return
  content.specs.splice(idx, 1)
  delete content.fontSizes[`spec.${specId}.label`]
  delete content.fontSizes[`spec.${specId}.value`]
  if (activeSyncKey.value?.startsWith(`spec.${specId}.`)) {
    activeSyncKey.value = ''
  }
  scheduleOverflowCheck()
}

const noticeOpen = ref(false)
const noticeText = ref('')

function showNotice(text) {
  noticeText.value = text
  noticeOpen.value = true
}

function removeVariant(variantId) {
  if (variants.value.length <= 1) {
    showNotice('至少保留一张缩略图')
    return
  }
  const idx = variants.value.findIndex((v) => v.id === variantId)
  if (idx < 0) return
  variants.value.splice(idx, 1)
  if (props.activeId === variantId) {
    const next = variants.value[Math.max(0, idx - 1)] || variants.value[0]
    emit('update:activeId', next.id)
  }
}
</script>

<template>
  <div class="board-wrap">
  <article
    ref="boardEl"
    class="board"
    :class="[`theme-${resolvedThemeId}`, { 'is-editing': editing }]"
    :style="boardStyle"
    @paste="onPastePlain"
    @focusin="onBoardFocusIn"
    @input="onBoardInput"
  >
    <div
      v-if="editing && activeSyncKey"
      class="font-size-bar"
    >
      <span class="font-size-bar-label">字号</span>
      <button
        type="button"
        class="fs-btn"
        title="减小"
        @mousedown.prevent
        @click="adjustFontSize(-1)"
      >
        −
      </button>
      <input
        class="fs-input"
        type="number"
        v-model.number="fontSizeDraft"
        :min="FONT_SIZE_MIN"
        :max="FONT_SIZE_MAX"
        @focus="onFontSizeFocus"
        @blur="commitFontSizeDraft"
        @keydown="onFontSizeKeydown"
      />
      <span class="fs-unit">px</span>
      <button
        type="button"
        class="fs-btn"
        title="增大"
        @mousedown.prevent
        @click="adjustFontSize(1)"
      >
        +
      </button>
      <button
        type="button"
        class="fs-reset"
        :disabled="content.fontSizes[activeSyncKey] == null"
        @mousedown.prevent
        @click="resetActiveFontSize(); syncFontSizeDraft()"
      >
        重置
      </button>
    </div>

    <section class="visual">
      <div
        class="stage"
        :style="{ backgroundColor: content.stageBg }"
      >
        <label v-if="editing" class="bg-picker stage-bg-picker" title="主图区背景色">
          <span>主图底色</span>
          <input v-model="content.stageBg" type="color" />
        </label>

        <div class="price-tag">
          <span
            class="price-label"
            data-sync="priceLabel"
            :style="fontStyle('priceLabel')"
            :contenteditable="editing"
            spellcheck="false"
            @keydown="onEditKeydown"
            @blur="(e) => syncText(e, (v) => { if (v) content.priceLabel = v })"
          >{{ content.priceLabel }}</span>
          <strong
            class="price-value"
            data-sync="priceValue"
            :style="fontStyle('priceValue')"
            :contenteditable="editing"
            spellcheck="false"
            @keydown="onEditKeydown"
            @blur="(e) => syncText(e, (v) => { if (v) content.priceValue = v })"
          >{{ content.priceValue }}</strong>
        </div>

        <img
          class="hero-image"
          :key="active.id"
          :src="active.image"
          :alt="`${content.brandZh}德训鞋 · ${active.name}`"
          draggable="false"
        />

        <div
          class="feature-chip"
          data-sync="featureChip"
          :style="fontStyle('featureChip')"
          :contenteditable="editing"
          spellcheck="false"
          @keydown="onEditKeydown"
          @blur="(e) => syncText(e, (v) => { if (v) content.featureChip = v })"
        >{{ content.featureChip }}</div>
      </div>

      <div
        class="thumbs"
        :class="{ 'thumbs--editing': editing }"
        role="tablist"
        aria-label="配色切换"
      >
        <label v-if="editing" class="bg-picker thumbs-bg-picker" title="缩略图背景色">
          <span>缩略图底色</span>
          <input v-model="content.thumbBg" type="color" />
        </label>

        <div
          v-for="item in variants"
          :key="item.id"
          class="thumb-wrap"
        >
          <button
            type="button"
            role="tab"
            class="thumb"
            :class="{ active: item.id === active.id }"
            :style="{ backgroundColor: content.thumbBg }"
            :aria-selected="item.id === active.id"
            :title="item.name"
            @click="selectVariant(item.id)"
          >
            <img :src="item.image" :alt="item.name" draggable="false" />
          </button>

          <div v-if="editing" class="thumb-actions">
            <button
              type="button"
              class="img-action tiny"
              title="替换图片"
              @click.stop="openReplaceUpload(item.id)"
            >
              传
            </button>
            <button
              type="button"
              class="img-action tiny danger"
              title="删除此缩略图"
              @click.stop="removeVariant(item.id)"
            >
              删
            </button>
          </div>
        </div>

        <button
          v-if="editing"
          type="button"
          class="thumb thumb-add"
          title="新增缩略图"
          @click="openAddUpload"
        >
          <span>+</span>
        </button>
      </div>
    </section>

    <input
      ref="fileInputRef"
      class="sr-only"
      type="file"
      accept="image/*"
      @change="onFilePicked"
    />

    <ImageCropDialog
      :open="cropOpen"
      :source-url="cropSource"
      :output-width="HERO_OUTPUT_WIDTH"
      @close="closeCrop"
      @confirm="onCropConfirm"
    />

    <section class="info">
      <header class="brand-row">
        <div class="brand">
          <h1
            data-sync="brandZh"
            :style="fontStyle('brandZh')"
            :contenteditable="editing"
            spellcheck="false"
            @keydown="onEditKeydown"
            @blur="(e) => syncText(e, (v) => { if (v) content.brandZh = v })"
          >{{ content.brandZh }}</h1>
          <p
            data-sync="brandEn"
            :style="fontStyle('brandEn')"
            :contenteditable="editing"
            spellcheck="false"
            @keydown="onEditKeydown"
            @blur="(e) => syncText(e, (v) => { if (v) content.brandEn = v })"
          >{{ content.brandEn }}</p>
        </div>
        <div class="style-no">
          <span
            data-sync="styleLabel"
            :style="fontStyle('styleLabel')"
            :contenteditable="editing"
            spellcheck="false"
            @keydown="onEditKeydown"
            @blur="(e) => syncText(e, (v) => { if (v) content.styleLabel = v })"
          >{{ content.styleLabel }}</span>
          <strong
            data-sync="styleNo"
            :style="fontStyle('styleNo')"
            :contenteditable="editing"
            spellcheck="false"
            @keydown="onEditKeydown"
            @blur="(e) => syncText(e, (v) => { if (v) content.styleNo = v })"
          >{{ content.styleNo }}</strong>
        </div>
      </header>

      <div class="divider" />

      <div class="title-block">
        <h2
          data-sync="title"
          :style="fontStyle('title')"
          :contenteditable="editing"
          spellcheck="false"
          @keydown="onEditKeydown"
          @blur="(e) => syncText(e, (v) => { if (v) content.title = v })"
        >{{ content.title }}</h2>
        <p
          data-sync="subtitle"
          :style="fontStyle('subtitle')"
          :contenteditable="editing"
          spellcheck="false"
          @keydown="onEditKeydown"
          @blur="(e) => syncText(e, (v) => { if (v) content.subtitle = v })"
        >{{ content.subtitle }}</p>
      </div>

      <div class="specs-block">
        <div class="specs-title">
          <i />
          <span
            data-sync="specsTitle"
            :style="fontStyle('specsTitle')"
            :contenteditable="editing"
            spellcheck="false"
            @keydown="onEditKeydown"
            @blur="(e) => syncText(e, (v) => { if (v) content.specsTitle = v })"
          >{{ content.specsTitle }}</span>
          <button
            v-if="editing"
            type="button"
            class="spec-add-btn"
            @click="addSpec"
          >
            添加参数
          </button>
        </div>
        <div v-if="content.specs.length" class="specs-grid">
          <div
            v-for="spec in content.specs"
            :key="spec.id"
            class="spec-cell"
          >
            <i class="dot" />
            <div>
              <span
                class="spec-label"
                :data-sync="`spec.${spec.id}.label`"
                :style="fontStyle(`spec.${spec.id}.label`)"
                :contenteditable="editing"
                spellcheck="false"
                @keydown="onEditKeydown"
                @blur="(e) => syncText(e, (v) => { if (v) spec.label = v })"
              >{{ spec.label }}</span>
              <strong
                class="spec-value"
                :data-sync="`spec.${spec.id}.value`"
                :style="fontStyle(`spec.${spec.id}.value`)"
                :contenteditable="editing"
                spellcheck="false"
                @keydown="onEditKeydown"
                @blur="(e) => syncText(e, (v) => { if (v) spec.value = v })"
              >{{ spec.value }}</strong>
            </div>
            <button
              v-if="editing"
              type="button"
              class="spec-remove"
              title="删除此参数"
              @mousedown.prevent
              @click="removeSpec(spec.id)"
            >
              删
            </button>
          </div>
        </div>
      </div>

      <button
        v-if="editing && !content.showFormulaBlock"
        type="button"
        class="formula-block-restore"
        @click="content.showFormulaBlock = true"
      >
        显示底部信息块
      </button>

      <div
        v-if="content.showFormulaBlock"
        class="formula"
        :class="{ 'formula--no-math': !content.showFormulaMath }"
      >
        <div v-if="editing" class="formula-toggles">
          <button
            type="button"
            class="formula-math-toggle"
            :title="content.showFormulaMath ? '隐藏右侧公式' : '显示右侧公式'"
            @click="content.showFormulaMath = !content.showFormulaMath"
          >
            {{ content.showFormulaMath ? '隐藏公式' : '显示公式' }}
          </button>
          <button
            type="button"
            class="formula-block-toggle"
            title="隐藏整块"
            @click="content.showFormulaBlock = false"
          >
            隐藏整块
          </button>
        </div>

        <div class="formula-copy">
          <h3
            data-sync="formulaTitle"
            :style="fontStyle('formulaTitle')"
            :contenteditable="editing"
            spellcheck="false"
            @keydown="onEditKeydown"
            @blur="(e) => syncText(e, (v) => { if (v) content.formulaTitle = v })"
          >{{ content.formulaTitle }}</h3>
          <p class="formula-lines">
            <span
              class="formula-line"
              data-sync="formulaLine1"
              :style="fontStyle('formulaLine1')"
              :contenteditable="editing"
              spellcheck="false"
              @keydown="onEditKeydown"
              @blur="(e) => syncText(e, (v) => { if (v) content.formulaLine1 = v })"
            >{{ content.formulaLine1 }}</span>
            <span
              class="formula-line"
              data-sync="formulaLine2"
              :style="fontStyle('formulaLine2')"
              :contenteditable="editing"
              spellcheck="false"
              @keydown="onEditKeydown"
              @blur="(e) => syncText(e, (v) => { if (v) content.formulaLine2 = v })"
            >{{ content.formulaLine2 }}</span>
          </p>
        </div>

        <div v-if="content.showFormulaMath" class="formula-math">
          <template v-for="(item, index) in content.formulaNums" :key="index">
            <span v-if="index === 1" class="op">+</span>
            <span v-if="index === 2" class="op">=</span>
            <div class="num-box" :class="{ highlight: index === 2 }">
              <strong
                :data-sync="`formulaNum.${index}.num`"
                :style="fontStyle(`formulaNum.${index}.num`)"
                :contenteditable="editing"
                spellcheck="false"
                @keydown="onEditKeydown"
                @blur="(e) => syncText(e, (v) => { if (v) item.num = v })"
              >{{ item.num }}</strong>
              <span
                :data-sync="`formulaNum.${index}.label`"
                :style="fontStyle(`formulaNum.${index}.label`)"
                :contenteditable="editing"
                spellcheck="false"
                @keydown="onEditKeydown"
                @blur="(e) => syncText(e, (v) => { if (v) item.label = v })"
              >{{ item.label }}</span>
            </div>
          </template>
        </div>
      </div>
    </section>
  </article>
  <p
    v-if="infoOverflow"
    class="overflow-warn"
    role="alert"
  >
    底部内容已超出 16:9 画布，导出时会被裁切。请减少换行或调小字号。
  </p>
  <AppModal
    :open="noticeOpen"
    title="无法删除"
    :message="noticeText"
    hide-cancel
    confirm-text="知道了"
    @close="noticeOpen = false"
    @confirm="noticeOpen = false"
  />
  </div>
</template>

<style scoped>
.board-wrap {
  position: relative;
  width: 100%;
  height: 100%;
}

.overflow-warn {
  position: absolute;
  left: 50%;
  bottom: 12px;
  transform: translateX(-50%);
  z-index: 40;
  max-width: calc(100% - 32px);
  margin: 0;
  padding: 8px 14px;
  border-radius: 999px;
  background: rgba(196, 92, 74, 0.96);
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.02em;
  text-align: center;
  line-height: 1.4;
  box-shadow: 0 8px 20px rgba(40, 30, 20, 0.2);
  pointer-events: none;
}

.board {
  position: relative;
  --ink: #1a1a1a;
  --muted: #8a857e;
  --line: #e6e1da;
  --chip: #9a6b52;
  --chip-fg: #fff;
  --chip-border: none;
  --chip-shadow: 0 8px 18px rgba(154, 107, 82, 0.28);
  --accent-hot: #c45c4a;
  --price-bg: #222;
  --price-fg: #fff;
  --price-border: none;
  --price-shadow: 0 10px 24px rgba(0, 0, 0, 0.18);
  --price-radius: 12px;
  --formula-bg: #2a2a2a;
  --formula-fg: #fff;
  --formula-muted: rgba(255, 255, 255, 0.72);
  --num-bg: #3a3a3a;
  --num-fg: #fff;
  --num-highlight-bg: #4a4038;
  --num-highlight-ring: rgba(201, 162, 39, 0.35);
  --op-fg: rgba(255, 255, 255, 0.55);
  --specs-bg: rgba(255, 255, 255, 0.45);
  --specs-radius: 12px;
  --board-radius: 18px;
  --stage-radius: 16px;
  --thumb-radius: 12px;
  --formula-radius: 14px;
  --chip-radius: 999px;
  --thumb-active: #c45c4a;
  --display-font: inherit;
  --info-bg: transparent;
  --info-pad: 4px 2px 0;
  --divider: linear-gradient(90deg, var(--line), transparent 95%);
  --board-pad: clamp(18px, 2vw, 28px);
  --board-gap: clamp(18px, 2.2vw, 32px);
  --visual-pad: 0;
  --thumbs-pad: 0;
  --formula-bleed: 0px;
  --edit-line: rgba(196, 92, 74, 0.55);
  --stage-bg: #ffffff;
  --thumb-bg: #ffffff;
  --board-solid: #f7f4ef;

  display: grid;
  grid-template-columns: 1.05fr 1fr;
  gap: var(--board-gap);
  width: 100%;
  height: 100%;
  aspect-ratio: 16 / 9;
  padding: var(--board-pad);
  box-sizing: border-box;
  background: linear-gradient(145deg, #f7f4ef 0%, #f0ebe3 55%, #ebe4db 100%);
  border-radius: var(--board-radius);
  overflow: hidden;
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.7) inset,
    0 24px 60px rgba(40, 30, 20, 0.12);
  font-family: inherit;
  color: var(--ink);
}

.visual {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-width: 0;
  padding: var(--visual-pad);
}

.stage {
  position: relative;
  flex: 1;
  background: var(--stage-bg);
  border-radius: var(--stage-radius);
  overflow: hidden;
  min-height: 0;
}

.hero-image {
  position: absolute;
  inset: 0;
  margin: auto;
  max-width: min(92%, 520px);
  max-height: 78%;
  width: auto;
  height: auto;
  object-fit: contain;
  user-select: none;
  animation: fade-in 0.28s ease;
}

@keyframes fade-in {
  from {
    opacity: 0;
    transform: translateY(6px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.price-tag {
  position: absolute;
  top: 16px;
  right: 16px;
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  padding: 10px 14px 12px;
  background: var(--price-bg);
  color: var(--price-fg);
  border: var(--price-border);
  border-radius: var(--price-radius);
  box-shadow: var(--price-shadow);
}

.price-label {
  font-size: 10px;
  letter-spacing: 0.06em;
  opacity: 0.75;
  font-weight: 500;
}

.price-value {
  font-size: clamp(26px, 2.6vw, 34px);
  line-height: 1;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.feature-chip {
  position: absolute;
  left: 18px;
  bottom: 18px;
  z-index: 2;
  padding: 8px 14px;
  background: var(--chip);
  color: var(--chip-fg);
  border: var(--chip-border);
  border-radius: var(--chip-radius);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.02em;
  box-shadow: var(--chip-shadow);
}

.thumbs {
  position: relative;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: flex-start;
  padding: var(--thumbs-pad);
}

.thumb-wrap {
  position: relative;
  flex: 0 0 96px;
  width: 96px;
}

.thumb {
  appearance: none;
  border: 2px solid transparent;
  background: var(--thumb-bg);
  border-radius: var(--thumb-radius);
  padding: 4px;
  cursor: pointer;
  width: 96px;
  height: 96px;
  aspect-ratio: 1;
  box-sizing: border-box;
  transition:
    border-color 0.2s ease,
    transform 0.2s ease,
    box-shadow 0.2s ease;
}

.thumb-add {
  flex: 0 0 96px;
  width: 96px;
  height: 96px;
  display: grid;
  place-items: center;
  border: 2px dashed color-mix(in srgb, var(--accent-hot) 55%, transparent);
  background: rgba(255, 255, 255, 0.65);
  color: var(--accent-hot);
}

.thumb-add span {
  font-size: 28px;
  font-weight: 300;
  line-height: 1;
}

.thumb img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
  pointer-events: none;
}

.thumb:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 16px rgba(40, 30, 20, 0.08);
}

.thumb.active {
  border-color: var(--thumb-active);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--thumb-active) 15%, transparent);
}

.info {
  display: flex;
  flex-direction: column;
  min-width: 0;
  padding: var(--info-pad);
  background: var(--info-bg);
}

.brand-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.brand h1 {
  margin: 0;
  font-family: var(--display-font);
  font-size: clamp(28px, 2.8vw, 40px);
  font-weight: 800;
  letter-spacing: 0.04em;
  color: var(--ink);
  line-height: 1.1;
}

.brand p {
  margin: 4px 0 0;
  font-size: 12px;
  letter-spacing: 0.18em;
  color: var(--muted);
  font-weight: 600;
}

.style-no {
  text-align: right;
  padding-top: 6px;
}

.style-no span {
  display: block;
  font-size: 11px;
  color: var(--muted);
  letter-spacing: 0.08em;
}

.style-no strong {
  display: block;
  margin-top: 4px;
  font-size: clamp(22px, 2.2vw, 28px);
  color: var(--ink);
  letter-spacing: 0.04em;
}

.divider {
  height: 1px;
  margin: 16px 0 18px;
  background: var(--divider);
}

.title-block h2 {
  margin: 0;
  font-family: var(--display-font);
  font-size: clamp(20px, 2.1vw, 28px);
  font-weight: 800;
  color: var(--ink);
  letter-spacing: 0.02em;
  line-height: 1.25;
}

.title-block p {
  margin: 10px 0 0;
  font-size: 13px;
  color: var(--muted);
  letter-spacing: 0.04em;
}

.specs-block {
  margin-top: auto;
  padding-top: 20px;
}

.specs-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 13px;
  font-weight: 700;
  color: var(--ink);
  letter-spacing: 0.04em;
}

.specs-title i {
  width: 3px;
  height: 14px;
  border-radius: 2px;
  background: var(--accent-hot);
}

.specs-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  border: 1px solid var(--line);
  border-radius: var(--specs-radius);
  overflow: hidden;
  background: var(--specs-bg);
}

.spec-add-btn {
  appearance: none;
  margin-left: auto;
  border: 1px dashed color-mix(in srgb, var(--accent-hot) 55%, transparent);
  background: rgba(255, 255, 255, 0.75);
  color: var(--accent-hot);
  border-radius: 999px;
  padding: 3px 10px;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
}

.spec-add-btn:hover {
  background: #fff;
}

.spec-cell {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 14px 16px;
  border-right: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
}

.spec-remove {
  appearance: none;
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 2;
  border: 1px solid rgba(160, 40, 40, 0.45);
  background: rgba(255, 255, 255, 0.94);
  color: #a02828;
  border-radius: 999px;
  padding: 1px 7px;
  font-size: 10px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 4px 10px rgba(40, 30, 20, 0.12);
}

.spec-remove:hover {
  background: #fff;
}

.board.is-editing .spec-cell {
  padding-right: 40px;
}

.spec-cell:nth-child(2n) {
  border-right: none;
}

.spec-cell:nth-last-child(-n + 2) {
  border-bottom: none;
}

.dot {
  width: 6px;
  height: 6px;
  margin-top: 7px;
  border-radius: 50%;
  background: var(--chip);
  flex-shrink: 0;
}

.spec-label {
  display: block;
  font-size: 11px;
  color: var(--muted);
  letter-spacing: 0.04em;
}

.spec-value {
  display: block;
  margin-top: 4px;
  font-size: 14px;
  font-weight: 700;
  color: var(--ink);
}

.formula {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-top: 16px;
  margin-left: var(--formula-bleed);
  margin-right: var(--formula-bleed);
  width: calc(100% - var(--formula-bleed) * 2);
  padding: 16px 18px;
  background: var(--formula-bg);
  color: var(--formula-fg);
  border-radius: var(--formula-radius);
}

.formula--no-math {
  justify-content: flex-start;
}

.formula-toggles {
  position: absolute;
  top: 8px;
  right: 10px;
  z-index: 2;
  display: flex;
  align-items: center;
  gap: 6px;
}

.formula-math-toggle,
.formula-block-toggle {
  appearance: none;
  border: 1px dashed rgba(255, 255, 255, 0.45);
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.95);
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}

.formula-math-toggle:hover,
.formula-block-toggle:hover {
  background: rgba(255, 255, 255, 0.18);
}

.formula-block-restore {
  appearance: none;
  align-self: flex-start;
  margin-top: 16px;
  border: 1px dashed color-mix(in srgb, var(--accent-hot) 55%, transparent);
  background: rgba(255, 255, 255, 0.65);
  color: var(--ink);
  border-radius: 999px;
  padding: 8px 14px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.formula-block-restore:hover {
  background: #fff;
}

.board.is-editing .formula {
  padding-top: 28px;
}

.formula-copy h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.formula-copy p,
.formula-lines {
  margin: 8px 0 0;
  font-size: 11px;
  line-height: 1.6;
  color: var(--formula-muted);
}

.formula-line {
  display: block;
}

.formula-math {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.num-box {
  min-width: 52px;
  padding: 8px 10px;
  text-align: center;
  background: var(--num-bg);
  color: var(--num-fg);
  border-radius: 10px;
}

.num-box.highlight {
  background: var(--num-highlight-bg);
  outline: 1px solid var(--num-highlight-ring);
}

.num-box strong {
  display: block;
  font-size: 24px;
  line-height: 1;
  font-weight: 800;
}

.num-box span {
  display: block;
  margin-top: 4px;
  font-size: 9px;
  color: color-mix(in srgb, var(--num-fg) 65%, transparent);
  letter-spacing: 0.02em;
}

.op {
  font-size: 18px;
  font-weight: 700;
  color: var(--op-fg);
}

.bg-picker {
  position: absolute;
  z-index: 5;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid color-mix(in srgb, var(--accent-hot) 45%, transparent);
  box-shadow: 0 4px 12px rgba(40, 30, 20, 0.1);
  font-size: 11px;
  font-weight: 600;
  color: #1a1a1a;
  cursor: pointer;
}

.bg-picker input[type='color'] {
  width: 22px;
  height: 22px;
  padding: 0;
  border: none;
  background: transparent;
  cursor: pointer;
}

.stage-bg-picker {
  top: 10px;
  left: 10px;
}

.thumbs-bg-picker {
  top: -34px;
  right: 0;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.thumb-actions {
  position: absolute;
  left: 50%;
  bottom: 6px;
  transform: translateX(-50%);
  z-index: 3;
  display: flex;
  gap: 4px;
}

.img-action {
  appearance: none;
  border: 1px solid color-mix(in srgb, var(--accent-hot) 50%, transparent);
  background: rgba(255, 255, 255, 0.94);
  color: #1a1a1a;
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 4px 10px rgba(40, 30, 20, 0.12);
}

.img-action:hover {
  background: #fff;
}

.img-action.danger {
  border-color: rgba(160, 40, 40, 0.45);
  color: #a02828;
}

.img-action.tiny {
  padding: 2px 7px;
  font-size: 10px;
  min-width: 24px;
}

.font-size-bar {
  position: absolute;
  top: 10px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 20;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid color-mix(in srgb, var(--accent-hot) 55%, transparent);
  box-shadow: 0 8px 24px rgba(40, 30, 20, 0.14);
  font-size: 12px;
  color: #1a1a1a;
}

.font-size-bar-label {
  font-weight: 700;
  letter-spacing: 0.04em;
  margin-right: 2px;
}

.fs-btn {
  appearance: none;
  width: 26px;
  height: 26px;
  border: 1px solid #d8d0c6;
  border-radius: 8px;
  background: #f7f4ef;
  color: #1a1a1a;
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
}

.fs-btn:hover {
  background: #fff;
  border-color: var(--accent-hot);
}

.fs-input {
  width: 44px;
  height: 26px;
  padding: 0 4px;
  border: 1px solid #d8d0c6;
  border-radius: 8px;
  text-align: center;
  font-size: 12px;
  font-weight: 700;
  color: #1a1a1a;
  background: #fff;
  -moz-appearance: textfield;
}

.fs-input::-webkit-outer-spin-button,
.fs-input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

.fs-unit {
  font-size: 11px;
  color: #8a857e;
  margin-left: -2px;
}

.fs-reset {
  appearance: none;
  border: none;
  background: transparent;
  color: var(--accent-hot);
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
  padding: 0 4px;
  min-width: 32px;
  flex-shrink: 0;
}

.fs-reset:hover:not(:disabled) {
  text-decoration: underline;
}

.fs-reset:disabled {
  opacity: 0.35;
  cursor: default;
}

.board [data-sync] {
  white-space: pre-wrap;
}

/* Edit mode: outline only */
.board.is-editing [contenteditable='true'] {
  cursor: text;
  outline: 1px dashed var(--edit-line);
  outline-offset: 2px;
  border-radius: 2px;
}

.board.is-editing [contenteditable='true']:focus {
  outline: 1px solid color-mix(in srgb, var(--accent-hot) 90%, transparent);
  background: color-mix(in srgb, var(--accent-hot) 8%, transparent);
}

.board.is-editing .feature-chip[contenteditable='true']:focus {
  color: #1a1a1a;
  background: #fff;
}

/* —— 夜宴：黑金时装 —— */
.board.theme-noir {
  --ink: #f3eadc;
  --board-solid: #100e0c;
  --muted: #9a9084;
  --line: rgba(212, 175, 103, 0.22);
  --chip: transparent;
  --chip-fg: #d4af67;
  --chip-border: 1px solid rgba(212, 175, 103, 0.7);
  --chip-shadow: none;
  --accent-hot: #d4af67;
  --price-bg: #0c0b0a;
  --price-fg: #e7c878;
  --price-border: 1px solid rgba(212, 175, 103, 0.55);
  --price-shadow: 0 12px 28px rgba(0, 0, 0, 0.35);
  --price-radius: 2px;
  --formula-bg: #0c0b0a;
  --formula-fg: #f3eadc;
  --formula-muted: rgba(243, 234, 220, 0.62);
  --num-bg: #1c1916;
  --num-fg: #f3eadc;
  --num-highlight-bg: #2a2318;
  --num-highlight-ring: rgba(212, 175, 103, 0.5);
  --op-fg: rgba(212, 175, 103, 0.7);
  --specs-bg: rgba(255, 255, 255, 0.03);
  --specs-radius: 2px;
  --board-radius: 10px;
  --stage-radius: 4px;
  --thumb-radius: 4px;
  --formula-radius: 4px;
  --chip-radius: 2px;
  --thumb-active: #d4af67;
  --edit-line: rgba(212, 175, 103, 0.55);
  background:
    radial-gradient(ellipse 70% 50% at 80% 0%, rgba(212, 175, 103, 0.08), transparent 50%),
    linear-gradient(165deg, #1a1815 0%, #100e0c 100%);
  box-shadow:
    0 0 0 1px rgba(212, 175, 103, 0.22) inset,
    0 28px 64px rgba(0, 0, 0, 0.4);
}

.board.theme-noir .brand h1,
.board.theme-noir .title-block h2 {
  font-weight: 700;
  letter-spacing: 0.12em;
}

.board.theme-noir .brand p {
  letter-spacing: 0.28em;
  color: #d4af67;
}

.board.theme-noir .specs-title i {
  width: 18px;
  height: 1px;
  border-radius: 0;
  background: #d4af67;
}

.board.theme-noir .thumb-add {
  background: rgba(255, 255, 255, 0.04);
  color: #d4af67;
}

.board.theme-noir.is-editing .feature-chip[contenteditable='true']:focus {
  color: #d4af67;
  background: #1c1a17;
}

/* —— 白场：极简展陈 —— */
.board.theme-studio {
  --ink: #111;
  --board-solid: #f7f7f5;
  --muted: #7a7a76;
  --line: #e6e6e2;
  --chip: #111;
  --chip-fg: #fff;
  --chip-shadow: none;
  --accent-hot: #111;
  --price-bg: #fff;
  --price-fg: #111;
  --price-border: 1px solid #111;
  --price-shadow: none;
  --price-radius: 2px;
  --formula-bg: #f3f3f0;
  --formula-fg: #111;
  --formula-muted: #6a6a66;
  --num-bg: #fff;
  --num-fg: #111;
  --num-highlight-bg: #111;
  --num-highlight-ring: transparent;
  --op-fg: #111;
  --specs-bg: transparent;
  --specs-radius: 0;
  --board-radius: 6px;
  --stage-radius: 0;
  --thumb-radius: 2px;
  --formula-radius: 0;
  --chip-radius: 2px;
  --thumb-active: #111;
  --edit-line: rgba(17, 17, 17, 0.45);
  --divider: #111;
  background: #f7f7f5;
  box-shadow: 0 0 0 1px #e4e4e0, 0 18px 40px rgba(20, 20, 18, 0.06);
}

.board.theme-studio .divider {
  height: 2px;
  width: 48px;
  margin: 18px 0 20px;
}

.board.theme-studio .brand h1 {
  font-weight: 700;
  letter-spacing: -0.03em;
}

.board.theme-studio .title-block h2 {
  font-weight: 600;
  letter-spacing: -0.02em;
}

.board.theme-studio .specs-grid {
  border: none;
  border-top: 1px solid var(--line);
  border-radius: 0;
}

.board.theme-studio .spec-cell {
  border-right: none;
  border-bottom: 1px solid var(--line);
  padding: 12px 0 12px 2px;
}

.board.theme-studio .spec-cell:nth-child(odd) {
  padding-right: 18px;
}

.board.theme-studio .spec-cell:nth-last-child(-n + 2) {
  border-bottom: none;
}

.board.theme-studio .specs-title i {
  width: 12px;
  height: 12px;
  border-radius: 0;
  background: #111;
}

.board.theme-studio .num-box.highlight {
  color: #fff;
}

.board.theme-studio .num-box.highlight span {
  color: rgba(255, 255, 255, 0.65);
}

.board.theme-studio .price-label {
  opacity: 1;
  color: #111;
}

.board.theme-studio .thumb-add {
  background: #fff;
  color: #111;
  border-color: #111;
}

.board.theme-studio .formula-math-toggle,
.board.theme-studio .formula-block-toggle {
  border-color: rgba(17, 17, 17, 0.35);
  background: rgba(17, 17, 17, 0.06);
  color: #111;
}

/* —— 宣纸：东方水墨 —— */
.board.theme-ink {
  --ink: #1c1a17;
  --board-solid: #f6efe3;
  --muted: #8a7d6c;
  --line: #d8ccb8;
  --chip: transparent;
  --chip-fg: #8c2f24;
  --chip-border: 1px solid #8c2f24;
  --chip-shadow: none;
  --accent-hot: #8c2f24;
  --price-bg: #b33328;
  --price-fg: #f8efe4;
  --price-shadow: none;
  --price-radius: 3px;
  --formula-bg: #1f1c18;
  --formula-fg: #f4eadc;
  --formula-muted: rgba(244, 234, 220, 0.7);
  --num-bg: #2c2722;
  --num-fg: #f4eadc;
  --num-highlight-bg: #8c2f24;
  --num-highlight-ring: transparent;
  --op-fg: rgba(244, 234, 220, 0.5);
  --specs-bg: rgba(255, 252, 246, 0.55);
  --specs-radius: 0;
  --board-radius: 4px;
  --stage-radius: 2px;
  --thumb-radius: 2px;
  --formula-radius: 2px;
  --chip-radius: 2px;
  --thumb-active: #8c2f24;
  --display-font: 'Noto Serif SC', 'Songti SC', 'SimSun', serif;
  --edit-line: rgba(140, 47, 36, 0.55);
  --divider: linear-gradient(90deg, #8c2f24, transparent 80%);
  background:
    repeating-linear-gradient(
      90deg,
      rgba(120, 90, 50, 0.03) 0 1px,
      transparent 1px 5px
    ),
    linear-gradient(180deg, #f6efe3 0%, #eee2cf 100%);
  box-shadow:
    0 0 0 1px rgba(140, 110, 70, 0.18) inset,
    0 22px 50px rgba(60, 42, 24, 0.12);
}

.board.theme-ink .price-tag {
  top: 18px;
  right: 18px;
  min-width: 84px;
  align-items: center;
  text-align: center;
  padding: 12px 10px 13px;
  box-shadow:
    0 0 0 2px #b33328,
    0 0 0 4px var(--stage-bg),
    0 0 0 5px #b33328;
}

.board.theme-ink .price-label {
  letter-spacing: 0.18em;
  opacity: 0.88;
}

.board.theme-ink .brand h1 {
  font-weight: 900;
  letter-spacing: 0.18em;
}

.board.theme-ink .title-block h2 {
  font-weight: 700;
  letter-spacing: 0.08em;
}

.board.theme-ink .divider {
  height: 2px;
}

.board.theme-ink .specs-grid {
  border-style: double;
  border-width: 3px;
}

.board.theme-ink .specs-title i {
  width: 10px;
  height: 10px;
  border-radius: 0;
  background: #8c2f24;
}

.board.theme-ink.is-editing .feature-chip[contenteditable='true']:focus {
  color: #8c2f24;
  background: #faf6ee;
}

/* —— 热卖：直播主推 —— */
.board.theme-live {
  --ink: #1a1a1a;
  --board-solid: #fff8f4;
  --muted: #8a7b74;
  --line: #f0d9d0;
  --chip: #e23c2f;
  --chip-fg: #fff;
  --chip-shadow: 0 8px 18px rgba(226, 60, 47, 0.28);
  --accent-hot: #e23c2f;
  --price-bg: #e23c2f;
  --price-fg: #fff;
  --price-shadow: 0 12px 24px rgba(226, 60, 47, 0.28);
  --price-radius: 16px 4px 16px 4px;
  --formula-bg: #1a1a1a;
  --formula-fg: #fff;
  --formula-muted: rgba(255, 255, 255, 0.72);
  --num-bg: #2c2c2c;
  --num-fg: #fff;
  --num-highlight-bg: #e23c2f;
  --num-highlight-ring: transparent;
  --op-fg: rgba(255, 255, 255, 0.55);
  --specs-bg: #fff;
  --specs-radius: 16px;
  --board-radius: 22px;
  --stage-radius: 20px;
  --thumb-radius: 16px;
  --formula-radius: 18px;
  --chip-radius: 999px;
  --thumb-active: #e23c2f;
  --edit-line: rgba(226, 60, 47, 0.55);
  background:
    radial-gradient(circle at 12% 18%, rgba(226, 60, 47, 0.1), transparent 32%),
    linear-gradient(145deg, #fff8f4 0%, #ffe9df 100%);
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.85) inset,
    0 24px 60px rgba(180, 60, 40, 0.12);
}

.board.theme-live .price-tag {
  padding: 12px 16px 14px;
}

.board.theme-live .price-value {
  font-weight: 800;
}

.board.theme-live .specs-title i {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.board.theme-live .dot {
  background: #e23c2f;
}

.board.theme-live .brand h1 {
  letter-spacing: 0.02em;
}

/* —— 刊页：杂志对开 —— */
.board.theme-folio {
  --ink: #2c241c;
  --board-solid: #ffffff;
  --muted: #8a7d6e;
  --line: #ddd3c6;
  --chip: #2c241c;
  --chip-fg: #f6efe6;
  --chip-shadow: none;
  --chip-radius: 0;
  --accent-hot: #c4a574;
  --price-bg: #2c241c;
  --price-fg: #f6efe6;
  --price-shadow: none;
  --price-radius: 0;
  --formula-bg: #2c241c;
  --formula-fg: #f6efe6;
  --formula-muted: rgba(246, 239, 230, 0.68);
  --num-bg: #3a3228;
  --num-fg: #f6efe6;
  --num-highlight-bg: #c4a574;
  --num-highlight-ring: transparent;
  --op-fg: rgba(246, 239, 230, 0.5);
  --specs-bg: transparent;
  --specs-radius: 0;
  --board-radius: 8px;
  --stage-radius: 0;
  --thumb-radius: 0;
  --formula-radius: 0;
  --thumb-active: #2c241c;
  --display-font: 'Noto Serif SC', 'Songti SC', 'SimSun', serif;
  --info-bg: #f3ece1;
  --info-pad: 28px 30px 0;
  --board-pad: 0;
  --board-gap: 0;
  --visual-pad: 0 0 16px;
  --thumbs-pad: 0 16px;
  --formula-bleed: -30px;
  --edit-line: rgba(44, 36, 28, 0.45);
  --divider: #2c241c;
  gap: 0;
  padding: 0;
  background: #fff;
  box-shadow: 0 24px 60px rgba(40, 30, 20, 0.14);
}

.board.theme-folio .visual {
  background: #fff;
}

.board.theme-folio .price-tag {
  top: 0;
  right: 0;
  padding: 14px 18px 16px;
}

.board.theme-folio .feature-chip {
  left: 0;
  bottom: 0;
  border-radius: 0;
}

.board.theme-folio .divider {
  height: 2px;
  width: 56px;
  margin: 16px 0 18px;
}

.board.theme-folio .brand h1 {
  font-weight: 900;
  letter-spacing: 0.08em;
}

.board.theme-folio .title-block h2 {
  font-weight: 700;
  line-height: 1.35;
}

.board.theme-folio .specs-grid {
  border: none;
  border-top: 1px solid var(--line);
}

.board.theme-folio .spec-cell {
  border-right: none;
  padding-left: 0;
}

.board.theme-folio .spec-cell:nth-child(odd) {
  padding-right: 20px;
}

.board.theme-folio .specs-title i {
  width: 22px;
  height: 1px;
  border-radius: 0;
  background: #2c241c;
}

.board.theme-folio .num-box.highlight {
  color: #2c241c;
}

.board.theme-folio .num-box.highlight span {
  color: rgba(44, 36, 28, 0.7);
}

.board.theme-folio .thumb-add {
  background: #fff;
  color: #2c241c;
  border-color: #2c241c;
}

@media (max-width: 900px) {
  .font-size-bar {
    transform: translateX(-50%) scale(0.92);
    transform-origin: top center;
  }
}
</style>
