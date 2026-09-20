<script setup>
import { onBeforeUnmount, onMounted, reactive, ref, nextTick, watch } from 'vue'
import { domToCanvas } from 'modern-screenshot'
import ProductShowcase from './components/ProductShowcase.vue'
import AppModal from './components/AppModal.vue'

const activeId = ref('yellow')
const boardRef = ref(null)
const stageWrapRef = ref(null)
const showcaseRef = ref(null)
const editing = ref(false)
const historyOpen = ref(false)
const historyBusy = ref(false)
const histories = ref([])
const historyQuery = ref('')
const historyPage = ref(1)
const historyTotal = ref(0)
const historyHasMore = ref(false)
const historyLoading = ref(false)
const historyPull = ref(0)
const historyBodyRef = ref(null)
const HISTORY_PAGE_SIZE = 20
const currentCase = ref(null)
let skipAutoSave = false
let autoSaveTimer = null
let lastSavedJson = ''
let persistInFlight = false
let persistQueued = false
let autoSaveErrorAt = 0
const previewOpen = ref(false)
const previewUrl = ref('')
const previewName = ref('')
const previewZoomed = ref(false)
const rendering = ref(false)

const DESIGN_W = 1200
const DESIGN_H = Math.round((DESIGN_W * 9) / 16)
const viewScale = ref(1)
const isPortrait = ref(false)
const portraitDismissed = ref(false)
let scaleRo = null

function updateViewScale() {
  const wrap = stageWrapRef.value
  if (!wrap) return
  viewScale.value = Math.min(1, wrap.clientWidth / DESIGN_W)
}

function updateOrientation() {
  isPortrait.value = window.innerHeight > window.innerWidth + 48
  if (!isPortrait.value) portraitDismissed.value = false
  updateViewScale()
}

function toggleEditing() {
  if (editing.value) {
    showcaseRef.value?.flushEditableContent?.()
    persistCurrentCase()
  }
  editing.value = !editing.value
}

function pad(n) {
  return String(n).padStart(2, '0')
}

function formatStamp(date = new Date()) {
  return (
    `${date.getFullYear()}${pad(date.getMonth() + 1)}${pad(date.getDate())}` +
    `${pad(date.getHours())}${pad(date.getMinutes())}${pad(date.getSeconds())}`
  )
}

function formatTime(iso) {
  const date = iso ? new Date(iso) : new Date()
  if (Number.isNaN(date.getTime())) return iso || ''
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function formatHistoryTime(iso) {
  const date = iso ? new Date(iso) : null
  if (!date || Number.isNaN(date.getTime())) return iso || ''
  const now = new Date()
  const sameDay =
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate()
  const clock = `${pad(date.getHours())}:${pad(date.getMinutes())}`
  if (sameDay) return `今天 ${clock}`
  const yesterday = new Date(now)
  yesterday.setDate(now.getDate() - 1)
  if (
    date.getFullYear() === yesterday.getFullYear() &&
    date.getMonth() === yesterday.getMonth() &&
    date.getDate() === yesterday.getDate()
  ) {
    return `昨天 ${clock}`
  }
  if (date.getFullYear() === now.getFullYear()) {
    return `${date.getMonth() + 1}月${date.getDate()}日 ${clock}`
  }
  return formatTime(iso)
}

async function api(path, options = {}) {
  const res = await fetch(path, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
  })
  const text = await res.text()
  let data = null
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = text
    }
  }
  if (!res.ok) {
    const detail = data?.detail
    const msg =
      typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail.map((item) => item.msg || item).join('; ')
          : res.statusText
    throw new Error(msg || '请求失败')
  }
  return data
}

function historyListUrl(page) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(HISTORY_PAGE_SIZE),
  })
  const keyword = historyQuery.value.trim()
  if (keyword) params.set('q', keyword)
  return `/api/histories?${params}`
}

async function loadHistories({ reset = false } = {}) {
  if (historyLoading.value) return
  if (reset) historyPage.value = 1
  else if (!historyHasMore.value && histories.value.length) return

  const page = reset ? 1 : historyPage.value
  historyLoading.value = true
  try {
    const data = await api(historyListUrl(page))
    const items = Array.isArray(data?.items) ? data.items : []
    historyTotal.value = Number(data?.total) || 0
    historyHasMore.value = Boolean(data?.has_more)
    historyPage.value = page
    if (reset) {
      histories.value = items
      await nextTick()
      if (historyBodyRef.value) historyBodyRef.value.scrollTop = 0
    } else {
      const seen = new Set(histories.value.map((item) => item.id))
      histories.value.push(...items.filter((item) => !seen.has(item.id)))
    }
  } catch (err) {
    console.error(err)
    if (reset) {
      histories.value = []
      historyTotal.value = 0
      historyHasMore.value = false
    }
  } finally {
    historyLoading.value = false
  }
}

async function loadMoreHistories() {
  if (historyLoading.value || !historyHasMore.value) return
  historyPage.value += 1
  await loadHistories()
}

function onHistoryScroll(e) {
  const el = e.currentTarget
  if (!(el instanceof HTMLElement)) return
  if (el.scrollTop + el.clientHeight >= el.scrollHeight - 56) {
    loadMoreHistories()
  }
}

let pullStartY = 0
let pullArmed = false

function onHistoryTouchStart(e) {
  const el = historyBodyRef.value
  if (!el || el.scrollTop > 2) {
    pullArmed = false
    return
  }
  pullStartY = e.touches[0].clientY
  pullArmed = true
}

function onHistoryTouchMove(e) {
  if (!pullArmed) return
  const el = historyBodyRef.value
  if (!el || el.scrollTop > 2) {
    pullArmed = false
    historyPull.value = 0
    return
  }
  const dy = e.touches[0].clientY - pullStartY
  if (dy <= 0) {
    historyPull.value = 0
    return
  }
  historyPull.value = Math.min(76, dy * 0.42)
  if (dy > 10) e.preventDefault()
}

async function onHistoryTouchEnd() {
  const shouldRefresh = historyPull.value > 46
  historyPull.value = 0
  pullArmed = false
  if (shouldRefresh) await loadHistories({ reset: true })
}

let searchTimer = null
watch(historyQuery, () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    if (historyOpen.value) loadHistories({ reset: true })
  }, 280)
})

const modal = reactive({
  open: false,
  title: '',
  message: '',
  input: false,
  inputValue: '',
  confirmText: '确定',
  cancelText: '取消',
  hideCancel: false,
  danger: false,
})
let modalDone = null

function showModal(opts) {
  Object.assign(modal, {
    title: '',
    message: '',
    input: false,
    inputValue: '',
    confirmText: '确定',
    cancelText: '取消',
    hideCancel: false,
    danger: false,
    ...opts,
    open: true,
  })
  return new Promise((resolve) => {
    modalDone = resolve
  })
}

function finishModal(value) {
  modal.open = false
  modalDone?.(value)
  modalDone = null
}

function notice(title, message) {
  return showModal({
    title,
    message,
    hideCancel: true,
    confirmText: '知道了',
  })
}

async function getBoardSnapshot() {
  return showcaseRef.value?.getSnapshot?.() || null
}

async function persistCurrentCase() {
  if (skipAutoSave || !currentCase.value) return
  if (persistInFlight) {
    persistQueued = true
    return
  }
  const snapshot = await getBoardSnapshot()
  if (!snapshot) return
  const json = JSON.stringify(snapshot)
  if (json === lastSavedJson) return
  const caseId = currentCase.value.id
  persistInFlight = true
  try {
    const saved = await api(`/api/histories/${caseId}`, {
      method: 'PATCH',
      body: JSON.stringify({ payload: snapshot }),
    })
    if (currentCase.value?.id === caseId) {
      currentCase.value = { id: saved.id, name: saved.name }
      lastSavedJson = json
    }
  } catch (err) {
    console.error(err)
    const now = Date.now()
    if (now - autoSaveErrorAt > 8000) {
      autoSaveErrorAt = now
      await notice('自动保存失败', err.message || '请确认后端已启动')
    }
  } finally {
    persistInFlight = false
    if (persistQueued && !skipAutoSave) {
      persistQueued = false
      persistCurrentCase()
    } else {
      persistQueued = false
    }
  }
}

function scheduleAutoSave() {
  if (skipAutoSave || !currentCase.value) return
  clearTimeout(autoSaveTimer)
  autoSaveTimer = setTimeout(() => {
    persistCurrentCase()
  }, 700)
}

function onBoardChange() {
  scheduleAutoSave()
}

async function startNewCase() {
  const ok = await showModal({
    title: '创建新案例？',
    message: '会离开当前历史案例，画板恢复为默认模板。当前案例的修改会先自动保存。',
    confirmText: '创建新案例',
  })
  if (!ok) return
  await persistCurrentCase()
  skipAutoSave = true
  clearTimeout(autoSaveTimer)
  currentCase.value = null
  lastSavedJson = ''
  showcaseRef.value?.resetToDefault?.()
  historyOpen.value = false
  await nextTick()
  skipAutoSave = false
}

async function createHistoryRecord() {
  const snapshot = await getBoardSnapshot()
  if (!snapshot) {
    await notice('无法保存', '读不到当前画板数据')
    return
  }
  const fallback = currentCase.value?.name
    ? `${currentCase.value.name} 副本`
    : `${snapshot.content?.title || '展示'} ${formatTime()}`
  const name = await showModal({
    title: '保存到历史',
    message: '当前画板会存成一条新的历史记录，不会覆盖已打开的案例。',
    input: true,
    inputValue: fallback,
    confirmText: '创建',
  })
  if (name == null) return
  historyBusy.value = true
  try {
    const created = await api('/api/histories', {
      method: 'POST',
      body: JSON.stringify({ name, payload: snapshot }),
    })
    currentCase.value = { id: created.id, name: created.name }
    lastSavedJson = JSON.stringify(snapshot)
    historyOpen.value = true
    await loadHistories({ reset: true })
  } catch (err) {
    console.error(err)
    await notice('创建失败', err.message || '请确认后端已启动')
  } finally {
    historyBusy.value = false
  }
}

async function restoreHistory(id) {
  if (currentCase.value?.id === id) {
    historyOpen.value = false
    return
  }
  const ok = await showModal({
    title: '打开这条记录？',
    message: currentCase.value
      ? '当前案例的修改会先自动保存，再打开所选记录。'
      : '当前画板会被覆盖。',
    confirmText: '打开',
  })
  if (!ok) return
  await persistCurrentCase()
  historyBusy.value = true
  skipAutoSave = true
  clearTimeout(autoSaveTimer)
  try {
    const record = await api(`/api/histories/${id}`)
    showcaseRef.value?.applySnapshot?.(record.payload)
    currentCase.value = { id: record.id, name: record.name }
    lastSavedJson = JSON.stringify(record.payload || {})
    historyOpen.value = false
    await nextTick()
  } catch (err) {
    console.error(err)
    await notice('打开失败', err.message || '请稍后重试')
  } finally {
    historyBusy.value = false
    skipAutoSave = false
  }
}

async function renameHistory(item) {
  const name = await showModal({
    title: '重命名',
    message: '修改这条历史记录的名称。',
    input: true,
    inputValue: item.name,
    confirmText: '保存',
  })
  if (name == null) return
  historyBusy.value = true
  try {
    await api(`/api/histories/${item.id}`, {
      method: 'PATCH',
      body: JSON.stringify({ name }),
    })
    if (currentCase.value?.id === item.id) {
      currentCase.value = { id: item.id, name }
    }
    await loadHistories({ reset: true })
  } catch (err) {
    console.error(err)
    await notice('重命名失败', err.message || '请稍后重试')
  } finally {
    historyBusy.value = false
  }
}

async function deleteHistory(item) {
  const ok = await showModal({
    title: '删除记录',
    message: `「${item.name}」删除后不能恢复。`,
    confirmText: '删除',
    danger: true,
  })
  if (!ok) return
  historyBusy.value = true
  try {
    await api(`/api/histories/${item.id}`, { method: 'DELETE' })
    if (currentCase.value?.id === item.id) {
      skipAutoSave = true
      currentCase.value = null
      lastSavedJson = ''
      skipAutoSave = false
    }
    await loadHistories({ reset: true })
  } catch (err) {
    console.error(err)
    await notice('删除失败', err.message || '请稍后重试')
  } finally {
    historyBusy.value = false
  }
}

function toggleHistory() {
  historyOpen.value = !historyOpen.value
  if (historyOpen.value) loadHistories({ reset: true })
}

onMounted(() => {
  nextTick(() => {
    updateOrientation()
    if (stageWrapRef.value) {
      scaleRo = new ResizeObserver(updateOrientation)
      scaleRo.observe(stageWrapRef.value)
    }
  })
  window.addEventListener('resize', updateOrientation)
  window.addEventListener('orientationchange', updateOrientation)
})

onBeforeUnmount(() => {
  clearTimeout(autoSaveTimer)
  clearTimeout(searchTimer)
  persistCurrentCase()
  scaleRo?.disconnect()
  window.removeEventListener('resize', updateOrientation)
  window.removeEventListener('orientationchange', updateOrientation)
})

const TEXT_LOCK_SELECTORS = [
  '.brand h1',
  '.brand p',
  '.style-no span',
  '.style-no strong',
  '.title-block h2',
  '.title-block p',
  '.specs-title span',
  '.spec-label',
  '.spec-value',
  '.price-label',
  '.price-value',
  '.feature-chip',
  '.formula-copy h3',
  '.formula-copy p',
  '.num-box strong',
  '.num-box span',
]

function waitForImages(root) {
  return Promise.all(
    [...root.querySelectorAll('img')].map((img) => {
      if (img.complete && img.naturalWidth > 0) return Promise.resolve()
      return new Promise((resolve) => {
        img.addEventListener('load', resolve, { once: true })
        img.addEventListener('error', resolve, { once: true })
      })
    }),
  )
}

/** Lock live text box size so screenshot matches on-screen wrap behavior */
function lockTextMetrics(root) {
  const locked = []
  for (const sel of TEXT_LOCK_SELECTORS) {
    root.querySelectorAll(sel).forEach((el) => {
      if (!(el instanceof HTMLElement)) return
      const rect = el.getBoundingClientRect()
      const styles = getComputedStyle(el)
      const fontSize = parseFloat(styles.fontSize) || 14
      const lineHeight =
        styles.lineHeight === 'normal'
          ? fontSize * 1.2
          : parseFloat(styles.lineHeight) || fontSize * 1.2
      const hasBreak = (el.innerText || '').includes('\n')
      // Multi-line on screen → keep wrapping; single-line → prevent clone wrap drift
      const isWrapped = hasBreak || el.scrollHeight > lineHeight * 1.6

      locked.push({
        el,
        whiteSpace: el.style.whiteSpace,
        minWidth: el.style.minWidth,
        maxWidth: el.style.maxWidth,
        width: el.style.width,
        boxSizing: el.style.boxSizing,
      })

      const w = Math.max(1, Math.ceil(el.offsetWidth))
      el.style.boxSizing = 'border-box'

      if (isWrapped) {
        // Preserve the same wrap width as HTML (do NOT force nowrap)
        el.style.width = `${w}px`
        el.style.maxWidth = `${w}px`
        el.style.minWidth = `${w}px`
        el.style.whiteSpace = styles.whiteSpace === 'nowrap' ? 'normal' : styles.whiteSpace
      } else {
        // Single line on screen: stop export from wrapping early
        el.style.whiteSpace = 'nowrap'
        el.style.minWidth = `${w + 1}px`
        el.style.maxWidth = 'none'
      }
    })
  }
  return () => {
    locked.forEach(({ el, whiteSpace, minWidth, maxWidth, width, boxSizing }) => {
      el.style.whiteSpace = whiteSpace
      el.style.minWidth = minWidth
      el.style.maxWidth = maxWidth
      el.style.width = width
      el.style.boxSizing = boxSizing
    })
  }
}

async function renderPromoPng() {
  const shell = boardRef.value
  const board = shell?.querySelector('.board')
  if (!board) throw new Error('未找到展示面板')

  const wasEditing = editing.value
  const prevScale = viewScale.value
  editing.value = false
  viewScale.value = 1
  let unlock = null
  try {
    await nextTick()
    await document.fonts.ready
    await waitForImages(board)
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))

    unlock = lockTextMetrics(board)
    await nextTick()
    await new Promise((r) => requestAnimationFrame(r))

    const width = DESIGN_W
    const height = DESIGN_H
    const targetWidth = 1920
    const targetHeight = 1080
    const exportScale = Math.min(3, Math.max(2, targetWidth / width))

    const captured = await domToCanvas(board, {
      width,
      height,
      scale: exportScale,
      backgroundColor: '#f7f4ef',
      style: {
        margin: '0',
        transform: 'none',
        width: `${width}px`,
        height: `${height}px`,
      },
    })

    if (!captured.width || !captured.height) {
      throw new Error('导出画布为空')
    }

    const out = document.createElement('canvas')
    out.width = targetWidth
    out.height = targetHeight
    const ctx = out.getContext('2d')
    ctx.imageSmoothingEnabled = true
    ctx.imageSmoothingQuality = 'high'
    ctx.fillStyle = '#f7f4ef'
    ctx.fillRect(0, 0, targetWidth, targetHeight)

    const ratio = Math.min(targetWidth / captured.width, targetHeight / captured.height)
    ctx.drawImage(
      captured,
      (targetWidth - captured.width * ratio) / 2,
      (targetHeight - captured.height * ratio) / 2,
      captured.width * ratio,
      captured.height * ratio,
    )

    return out.toDataURL('image/png')
  } finally {
    unlock?.()
    viewScale.value = prevScale
    editing.value = wasEditing
  }
}

function downloadPng(url, name) {
  const link = document.createElement('a')
  link.download = name
  link.href = url
  link.click()
}

async function savePromoImage() {
  if (rendering.value) return
  rendering.value = true
  try {
    const url = await renderPromoPng()
    downloadPng(url, `${formatStamp()}.png`)
  } catch (err) {
    console.error(err)
    await notice('保存失败', err.message === '未找到展示面板' ? '未找到展示面板' : '生成图片时出错，请重试')
  } finally {
    rendering.value = false
  }
}

async function openPreview() {
  if (rendering.value) return
  rendering.value = true
  try {
    previewUrl.value = await renderPromoPng()
    previewName.value = `${formatStamp()}.png`
    previewZoomed.value = false
    previewOpen.value = true
  } catch (err) {
    console.error(err)
    await notice('预览失败', err.message === '未找到展示面板' ? '未找到展示面板' : '生成预览时出错，请重试')
  } finally {
    rendering.value = false
  }
}

function closePreview() {
  previewOpen.value = false
  previewZoomed.value = false
  previewUrl.value = ''
  previewName.value = ''
}

function confirmDownload() {
  if (!previewUrl.value) return
  downloadPng(previewUrl.value, previewName.value || `${formatStamp()}.png`)
}
</script>

<template>
  <div class="page">
    <header class="toolbar">
      <div class="toolbar-text">
        <p class="eyebrow">PRODUCT SHOWCASE</p>
        <p v-if="currentCase" class="case-chip">当前案例：{{ currentCase.name }}</p>
      </div>
      <div class="toolbar-actions">
        <button
          v-if="currentCase"
          type="button"
          class="ghost-btn"
          :disabled="historyBusy"
          @click="startNewCase"
        >
          新的案例
        </button>
        <button
          type="button"
          class="ghost-btn"
          :class="{ active: historyOpen }"
          @click="toggleHistory"
        >
          历史案例
        </button>
        <button
          type="button"
          class="edit-btn"
          :class="{ active: editing }"
          @mousedown.prevent="editing && showcaseRef?.flushEditableContent?.()"
          @click="toggleEditing"
        >
          {{ editing ? '完成编辑' : '编辑模式' }}
        </button>
        <button
          type="button"
          class="save-btn"
          :disabled="rendering"
          @click="savePromoImage"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path
              d="M12 3v12m0 0 4-4m-4 4-4-4M5 19h14"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>
          {{ rendering ? '生成中…' : '保存图片' }}
        </button>
      </div>
    </header>

    <div
      v-if="historyOpen"
      class="history-mask"
      @click="historyOpen = false"
    />
    <aside
      class="history-panel"
      :class="{ open: historyOpen }"
      :aria-hidden="!historyOpen"
    >
      <div class="history-head">
        <div>
          <p class="history-kicker">ARCHIVE</p>
          <strong>历史案例</strong>
          <span class="history-count">{{ historyTotal }} 条</span>
        </div>
        <button type="button" class="history-close" @click="historyOpen = false">关闭</button>
      </div>

      <label class="history-search">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="11" cy="11" r="6.5" fill="none" stroke="currentColor" stroke-width="1.8" />
          <path d="M16.2 16.2 20 20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
        </svg>
        <input
          v-model="historyQuery"
          type="search"
          placeholder="搜索案例名称"
          autocomplete="off"
          @keydown.enter.prevent="loadHistories({ reset: true })"
        />
        <button
          v-if="historyQuery"
          type="button"
          class="history-search-clear"
          @click="historyQuery = ''"
        >
          清除
        </button>
      </label>

      <div
        ref="historyBodyRef"
        class="history-body"
        @scroll="onHistoryScroll"
        @touchstart.passive="onHistoryTouchStart"
        @touchmove="onHistoryTouchMove"
        @touchend="onHistoryTouchEnd"
      >
        <div
          class="history-pull"
          :class="{ ready: historyPull > 46, loading: historyLoading && historyPull === 0 }"
          :style="{ height: `${Math.max(historyPull, historyLoading && !histories.length ? 36 : 0)}px` }"
        >
          <span>{{ historyPull > 46 ? '松开刷新' : '下拉刷新' }}</span>
        </div>

        <p v-if="!histories.length && !historyLoading" class="history-empty">
          {{ historyQuery.trim() ? `没有找到「${historyQuery.trim()}」` : '还没有记录。编辑完成后点「保存到历史」。' }}
        </p>

        <ul v-else class="history-list">
          <li
            v-for="item in histories"
            :key="item.id"
            class="history-item"
            :class="{ current: currentCase?.id === item.id }"
          >
            <button
              type="button"
              class="history-main"
              :disabled="historyBusy"
              @click="restoreHistory(item.id)"
            >
              <span class="history-mark" aria-hidden="true" />
              <span class="history-copy">
                <span class="history-name">{{ item.name }}</span>
                <span class="history-time">{{ formatHistoryTime(item.created_at) }}</span>
              </span>
              <span v-if="currentCase?.id === item.id" class="history-now">当前</span>
            </button>
            <div class="history-ops">
              <button type="button" :disabled="historyBusy" @click="renameHistory(item)">改名</button>
              <button type="button" class="danger" :disabled="historyBusy" @click="deleteHistory(item)">删除</button>
            </div>
          </li>
        </ul>

        <p v-if="historyLoading && histories.length" class="history-status">加载中…</p>
        <p v-else-if="histories.length && !historyHasMore" class="history-status">已经到底了</p>
        <p v-else-if="historyHasMore" class="history-status">上拉加载更多</p>
      </div>
    </aside>

    <AppModal
      :open="modal.open"
      :title="modal.title"
      :message="modal.message"
      :input="modal.input"
      :input-value="modal.inputValue"
      :confirm-text="modal.confirmText"
      :cancel-text="modal.cancelText"
      :hide-cancel="modal.hideCancel"
      :danger="modal.danger"
      @close="finishModal(null)"
      @confirm="finishModal"
    />

    <div ref="stageWrapRef" class="stage-wrap">
      <div
        class="capture-shell"
        :style="{ height: `${Math.max(1, Math.round(DESIGN_H * viewScale))}px` }"
      >
        <div
          ref="boardRef"
          class="capture-inner"
          :style="{
            width: `${DESIGN_W}px`,
            height: `${DESIGN_H}px`,
            transform: `scale(${viewScale})`,
          }"
        >
          <ProductShowcase
            ref="showcaseRef"
            v-model:active-id="activeId"
            :editing="editing"
            @change="onBoardChange"
          />
        </div>
      </div>
    </div>

    <div class="board-footer">
      <button
        type="button"
        class="ghost-btn"
        :disabled="historyBusy"
        @click="createHistoryRecord"
      >
        {{ currentCase ? '另存为新记录' : '保存到历史' }}
      </button>
      <button
        type="button"
        class="ghost-btn"
        :disabled="rendering"
        @click="openPreview"
      >
        {{ rendering ? '生成中…' : '预览' }}
      </button>
    </div>

    <p class="hint">
      {{
        viewScale < 0.995
          ? '屏幕放不下完整画布，已按 16:9 缩小显示。可用预览查看 1920×1080 成品。'
          : editing
            ? '编辑模式：可改文字 · 可调字号 · 底部信息块可隐藏/显示 · 缩略图可传图/删除/新增'
            : '画布固定 16:9 · 导出尺寸 1920×1080'
      }}
    </p>

    <Teleport to="body">
      <div
        v-if="isPortrait && !portraitDismissed"
        class="rotate-mask"
        role="dialog"
        aria-modal="true"
      >
        <div class="rotate-card">
          <p class="rotate-kicker">LANDSCAPE</p>
          <h3>请先横过来</h3>
          <p>画布是 16:9。竖屏看不全、也容易点不到保存，把手机横过来再编辑和导出。</p>
          <div class="rotate-icon" aria-hidden="true">
            <span />
          </div>
          <button type="button" class="rotate-skip" @click="portraitDismissed = true">
            仍要竖屏使用
          </button>
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <div
        v-if="previewOpen"
        class="preview-mask"
        @click.self="closePreview"
      >
        <div class="preview-card" role="dialog" aria-modal="true">
          <header class="preview-head">
            <div>
              <p class="preview-kicker">PREVIEW</p>
              <h3>16:9 预览</h3>
            </div>
            <button type="button" class="preview-x" @click="closePreview">关闭</button>
          </header>
          <div class="preview-frame">
            <img
              v-if="previewUrl"
              :src="previewUrl"
              alt="16:9 宣传图预览"
              title="点击放大"
              @click="previewZoomed = true"
            />
          </div>
          <footer class="preview-foot">
            <button type="button" class="preview-btn ghost" @click="closePreview">关闭</button>
            <button type="button" class="preview-btn primary" @click="confirmDownload">下载图片</button>
          </footer>
        </div>
        <div
          v-if="previewZoomed"
          class="preview-zoom"
          @click="previewZoomed = false"
        >
          <img :src="previewUrl" alt="放大预览" />
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.page {
  min-height: 100vh;
  padding: 28px 24px 40px;
  box-sizing: border-box;
  background:
    radial-gradient(ellipse 80% 50% at 20% 0%, rgba(201, 162, 39, 0.08), transparent 55%),
    radial-gradient(ellipse 60% 40% at 90% 10%, rgba(154, 107, 82, 0.07), transparent 50%),
    #ebe6df;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px 16px;
  max-width: 1200px;
  margin: 0 auto 22px;
}

.toolbar-text {
  flex: 0 1 auto;
  min-width: 0;
}

.eyebrow {
  margin: 0;
  font-size: 11px;
  letter-spacing: 0.16em;
  color: #8a857e;
  font-weight: 600;
}

.case-chip {
  margin: 6px 0 0;
  font-size: 13px;
  font-weight: 700;
  color: #3b342c;
}

.toolbar-text h1 {
  margin: 6px 0 0;
  font-size: 22px;
  font-weight: 800;
  color: #1a1a1a;
  letter-spacing: 0.02em;
}

.save-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  appearance: none;
  border: none;
  cursor: pointer;
  padding: 12px 18px;
  border-radius: 999px;
  background: #1f1f1f;
  color: #fff;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.02em;
  box-shadow: 0 12px 28px rgba(20, 16, 12, 0.18);
  transition:
    transform 0.2s ease,
    opacity 0.2s ease,
    background 0.2s ease;
}

.toolbar-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  flex: 1 1 420px;
  min-width: 0;
}

.toolbar-actions > button {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  white-space: nowrap;
}

.ghost-btn {
  appearance: none;
  border: 1px solid #c4b8a8;
  cursor: pointer;
  padding: 11px 16px;
  border-radius: 999px;
  background: #fff;
  color: #1a1a1a;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.ghost-btn:hover:not(:disabled) {
  border-color: #c45c4a;
  color: #c45c4a;
}

.ghost-btn.active {
  border-color: #1f1f1f;
  background: #1f1f1f;
  color: #fff;
}

.ghost-btn:disabled {
  opacity: 0.65;
  cursor: wait;
}

.history-mask {
  position: fixed;
  inset: 0;
  z-index: 40;
  background: rgba(28, 22, 16, 0.28);
  backdrop-filter: blur(4px);
}

.history-panel {
  position: fixed;
  top: 12px;
  right: 12px;
  bottom: 12px;
  z-index: 41;
  display: flex;
  flex-direction: column;
  width: min(400px, calc(100vw - 24px));
  box-sizing: border-box;
  padding: 18px 16px 12px;
  border-radius: 24px;
  background:
    radial-gradient(ellipse 80% 40% at 100% 0%, rgba(201, 162, 39, 0.12), transparent 55%),
    linear-gradient(180deg, #fffdf8 0%, #f4efe7 100%);
  border: 1px solid rgba(255, 255, 255, 0.86);
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.8) inset,
    0 24px 50px rgba(40, 30, 20, 0.18);
  transform: translateX(calc(100% + 24px));
  transition: transform 0.24s ease;
  overflow: hidden;
}

.history-panel.open {
  transform: translateX(0);
}

.history-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
  padding: 0 4px;
}

.history-kicker {
  margin: 0 0 4px;
  font-size: 10px;
  letter-spacing: 0.18em;
  color: #8a857e;
  font-weight: 700;
}

.history-head strong {
  display: block;
  font-size: 22px;
  font-weight: 800;
  letter-spacing: 0.02em;
  color: #1a1a1a;
}

.history-count {
  display: inline-block;
  margin-top: 6px;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(196, 92, 74, 0.1);
  color: #9a5a48;
  font-size: 11px;
  font-weight: 700;
}

.history-search {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 4px 12px;
  padding: 0 12px;
  height: 42px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid #e7dfd3;
  box-shadow: 0 8px 18px rgba(40, 30, 20, 0.04);
  color: #8a857e;
}

.history-search svg {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

.history-search input {
  flex: 1;
  min-width: 0;
  height: 100%;
  border: none;
  outline: none;
  background: transparent;
  font-size: 14px;
  font-weight: 600;
  color: #1a1a1a;
}

.history-search-clear {
  appearance: none;
  border: none;
  background: transparent;
  color: #c45c4a;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  padding: 0;
}

.history-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 0 4px 8px;
  overscroll-behavior: contain;
}

.history-pull {
  display: flex;
  align-items: flex-end;
  justify-content: center;
  overflow: hidden;
  color: #8a857e;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.04em;
  transition: height 0.12s ease;
}

.history-pull.ready {
  color: #c45c4a;
}

.history-close,
.history-ops button {
  appearance: none;
  border: 1px solid #e3d9cc;
  background: #fff;
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  color: #1a1a1a;
}

.history-close:hover,
.history-ops button:hover:not(:disabled) {
  border-color: #c45c4a;
  color: #c45c4a;
}

.history-empty {
  margin: 48px 12px 0;
  color: #8a857e;
  font-size: 13px;
  line-height: 1.7;
  text-align: center;
}

.history-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.history-item {
  border: 1px solid rgba(227, 217, 204, 0.9);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.72);
  padding: 12px 12px 10px;
  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease,
    transform 0.2s ease;
}

.history-item:hover {
  border-color: #d5c6b3;
  box-shadow: 0 10px 24px rgba(40, 30, 20, 0.07);
  transform: translateY(-1px);
}

.history-item.current {
  border-color: rgba(196, 92, 74, 0.45);
  background: linear-gradient(180deg, #fff8f2, #fff);
  box-shadow: 0 10px 22px rgba(196, 92, 74, 0.08);
}

.history-main {
  appearance: none;
  width: 100%;
  border: none;
  background: transparent;
  text-align: left;
  cursor: pointer;
  padding: 0 0 10px;
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.history-mark {
  width: 8px;
  height: 8px;
  margin-top: 6px;
  border-radius: 50%;
  background: #d8cfc3;
  flex-shrink: 0;
}

.history-item.current .history-mark {
  background: #c45c4a;
  box-shadow: 0 0 0 4px rgba(196, 92, 74, 0.16);
}

.history-copy {
  flex: 1;
  min-width: 0;
}

.history-name {
  display: block;
  font-size: 14px;
  font-weight: 800;
  color: #1a1a1a;
  line-height: 1.4;
  word-break: break-word;
}

.history-time {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: #8a857e;
  font-weight: 600;
}

.history-now {
  flex-shrink: 0;
  margin-top: 2px;
  padding: 2px 8px;
  border-radius: 999px;
  background: #c45c4a;
  color: #fff;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.04em;
}

.history-ops {
  display: flex;
  gap: 6px;
  padding-left: 18px;
}

.history-ops .danger {
  color: #a02828;
  border-color: rgba(160, 40, 40, 0.28);
}

.history-status {
  margin: 14px 0 6px;
  text-align: center;
  color: #a39a90;
  font-size: 12px;
  font-weight: 600;
}

.edit-btn {
  appearance: none;
  border: 1px solid #c4b8a8;
  cursor: pointer;
  padding: 11px 16px;
  border-radius: 999px;
  background: #fff;
  color: #1a1a1a;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.02em;
  transition:
    background 0.2s ease,
    border-color 0.2s ease,
    color 0.2s ease;
}

.edit-btn:hover {
  background: #fff;
}

.edit-btn.active {
  border-color: #c45c4a;
  background: #c45c4a;
  color: #fff;
}

.save-btn svg {
  width: 18px;
  height: 18px;
}

.save-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  background: #333;
}

.save-btn:disabled {
  opacity: 0.65;
  cursor: wait;
}

.stage-wrap {
  max-width: 1200px;
  margin: 0 auto;
}

.board-footer {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  max-width: 1200px;
  margin: 16px auto 0;
}

.board-footer > button {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  white-space: nowrap;
}

.capture-shell {
  position: relative;
  width: 100%;
  overflow: hidden;
  border-radius: 18px;
}

.capture-inner {
  transform-origin: top left;
}

.capture-inner :deep(.board) {
  width: 100%;
  height: 100%;
}

.hint {
  max-width: 1200px;
  margin: 12px auto 0;
  text-align: center;
  font-size: 13px;
  color: #8a857e;
  padding: 0 12px;
}

.preview-mask {
  position: fixed;
  inset: 0;
  z-index: 10060;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px;
  padding-top: max(12px, env(safe-area-inset-top));
  padding-bottom: max(12px, env(safe-area-inset-bottom));
  overflow: auto;
  background: rgba(28, 22, 16, 0.52);
  backdrop-filter: blur(8px);
}

.preview-card {
  display: flex;
  flex-direction: column;
  width: min(920px, 100%);
  max-height: calc(100dvh - 24px);
  padding: 14px 16px 12px;
  border-radius: 20px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.75), rgba(255, 255, 255, 0.36)),
    #f7f4ef;
  border: 1px solid rgba(255, 255, 255, 0.7);
  box-shadow: 0 28px 60px rgba(40, 30, 20, 0.24);
}

.preview-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
  flex-shrink: 0;
}

.preview-kicker {
  margin: 0 0 4px;
  font-size: 10px;
  letter-spacing: 0.16em;
  color: #8a857e;
  font-weight: 700;
}

.preview-head h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 800;
}

.preview-head p {
  margin: 4px 0 0;
  font-size: 12px;
  color: #8a857e;
}

.preview-x,
.preview-btn {
  appearance: none;
  border: none;
  border-radius: 999px;
  font-weight: 700;
  cursor: pointer;
}

.preview-x {
  border: 1px solid #ddd4c8;
  background: #fff;
  color: #1a1a1a;
  padding: 6px 12px;
  font-size: 12px;
}

.preview-frame {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 14px;
  overflow: auto;
  background: #1a1a1a;
  box-shadow: 0 10px 24px rgba(40, 30, 20, 0.12);
}

.preview-frame img {
  display: block;
  max-width: 100%;
  max-height: min(56dvh, calc(100dvh - 168px));
  width: auto;
  height: auto;
  object-fit: contain;
  background: #f7f4ef;
  cursor: zoom-in;
}

.preview-zoom {
  position: fixed;
  inset: 0;
  z-index: 10080;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px;
  overflow: auto;
  background: rgba(12, 10, 8, 0.88);
  cursor: zoom-out;
}

.preview-zoom img {
  display: block;
  max-width: min(1920px, 100%);
  height: auto;
  margin: auto;
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.35);
}

.preview-foot {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 12px;
  flex-shrink: 0;
}

.preview-btn {
  min-width: 88px;
  padding: 10px 16px;
  font-size: 13px;
}

.preview-btn.ghost {
  background: #efeae3;
  color: #1a1a1a;
}

.preview-btn.primary {
  background: #1f1f1f;
  color: #fff;
}

.rotate-mask {
  position: fixed;
  inset: 0;
  z-index: 10100;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(28, 22, 16, 0.72);
  backdrop-filter: blur(10px);
}

.rotate-card {
  width: min(380px, 100%);
  padding: 28px 24px 22px;
  border-radius: 22px;
  text-align: center;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.8), rgba(255, 255, 255, 0.4)),
    #f7f4ef;
  border: 1px solid rgba(255, 255, 255, 0.7);
  box-shadow: 0 28px 60px rgba(40, 30, 20, 0.28);
}

.rotate-kicker {
  margin: 0 0 8px;
  font-size: 10px;
  letter-spacing: 0.18em;
  color: #8a857e;
  font-weight: 700;
}

.rotate-card h3 {
  margin: 0;
  font-size: 22px;
  font-weight: 800;
}

.rotate-card p {
  margin: 10px 0 0;
  font-size: 14px;
  line-height: 1.65;
  color: #6f6a63;
}

.rotate-icon {
  width: 72px;
  height: 44px;
  margin: 22px auto 8px;
  border: 3px solid #1a1a1a;
  border-radius: 10px;
  position: relative;
  animation: rotate-hint 1.8s ease-in-out infinite;
}

.rotate-icon span {
  position: absolute;
  right: 6px;
  top: 50%;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #c45c4a;
  transform: translateY(-50%);
}

@keyframes rotate-hint {
  0%,
  20% {
    transform: rotate(0deg);
  }
  50%,
  80% {
    transform: rotate(90deg);
  }
  100% {
    transform: rotate(0deg);
  }
}

.rotate-skip {
  appearance: none;
  margin-top: 18px;
  border: none;
  background: transparent;
  color: #8a857e;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 3px;
}

@media (orientation: landscape) and (max-height: 500px) {
  .preview-card {
    padding: 10px 12px 10px;
    max-height: calc(100dvh - 12px);
    border-radius: 16px;
  }

  .preview-head h3 {
    font-size: 15px;
  }

  .preview-head p,
  .preview-kicker {
    display: none;
  }

  .preview-frame img {
    max-height: calc(100dvh - 118px);
  }

  .preview-foot {
    margin-top: 8px;
  }

  .preview-btn {
    padding: 8px 14px;
  }

  .history-panel {
    top: 8px;
    right: 8px;
    bottom: 8px;
    width: min(340px, 48vw);
    padding: 14px 14px 16px;
  }
}

@media (max-width: 640px) {
  .toolbar {
    align-items: stretch;
  }

  .toolbar-actions {
    flex-basis: 100%;
    justify-content: flex-start;
  }
}
</style>
