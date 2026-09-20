<script setup>
import { onMounted, reactive, ref, nextTick } from 'vue'
import { domToCanvas } from 'modern-screenshot'
import ProductShowcase from './components/ProductShowcase.vue'
import AppModal from './components/AppModal.vue'

const activeId = ref('yellow')
const boardRef = ref(null)
const showcaseRef = ref(null)
const saving = ref(false)
const editing = ref(false)
const historyOpen = ref(false)
const historyBusy = ref(false)
const histories = ref([])

function toggleEditing() {
  if (editing.value) {
    showcaseRef.value?.flushEditableContent?.()
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

async function loadHistories() {
  try {
    histories.value = await api('/api/histories')
  } catch (err) {
    console.error(err)
    histories.value = []
  }
}

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

async function saveHistoryRecord() {
  showcaseRef.value?.flushEditableContent?.()
  const snapshot = showcaseRef.value?.getSnapshot?.()
  if (!snapshot) {
    await notice('无法保存', '读不到当前画板数据')
    return
  }
  const fallback = `${snapshot.content?.title || '展示'} ${formatTime()}`
  const name = await showModal({
    title: '保存记录',
    message: '给这次快照起个名字，方便之后找回。',
    input: true,
    inputValue: fallback,
    confirmText: '保存',
  })
  if (name == null) return
  historyBusy.value = true
  try {
    await api('/api/histories', {
      method: 'POST',
      body: JSON.stringify({ name, payload: snapshot }),
    })
    await loadHistories()
    historyOpen.value = true
  } catch (err) {
    console.error(err)
    await notice('保存失败', err.message || '请确认后端已启动')
  } finally {
    historyBusy.value = false
  }
}

async function restoreHistory(id) {
  const ok = await showModal({
    title: '恢复这条记录？',
    message: '当前画板会被覆盖，还没保存的修改会丢掉。',
    confirmText: '恢复',
  })
  if (!ok) return
  historyBusy.value = true
  try {
    const record = await api(`/api/histories/${id}`)
    showcaseRef.value?.applySnapshot?.(record.payload)
    historyOpen.value = false
  } catch (err) {
    console.error(err)
    await notice('恢复失败', err.message || '请稍后重试')
  } finally {
    historyBusy.value = false
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
    await loadHistories()
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
    await loadHistories()
  } catch (err) {
    console.error(err)
    await notice('删除失败', err.message || '请稍后重试')
  } finally {
    historyBusy.value = false
  }
}

function toggleHistory() {
  historyOpen.value = !historyOpen.value
  if (historyOpen.value) loadHistories()
}

onMounted(loadHistories)

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

      const w = Math.max(1, Math.ceil(rect.width))
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

async function savePromoImage() {
  const shell = boardRef.value
  if (!shell || saving.value) return

  const board = shell.querySelector('.board')
  if (!board) {
    await notice('无法导出', '未找到展示面板')
    return
  }

  saving.value = true
  const wasEditing = editing.value
  editing.value = false
  let unlock = null
  try {
    await nextTick()
    await document.fonts.ready
    await waitForImages(board)
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))

    unlock = lockTextMetrics(board)
    await nextTick()
    await new Promise((r) => requestAnimationFrame(r))

    const width = Math.max(1, Math.round(board.offsetWidth))
    const height = Math.max(1, Math.round(board.offsetHeight))
    if (width < 2 || height < 2) {
      throw new Error(`面板尺寸异常: ${width}x${height}`)
    }

    const targetWidth = 1920
    const targetHeight = 1080
    const scale = Math.min(3, Math.max(2, targetWidth / width))

    const captured = await domToCanvas(board, {
      width,
      height,
      scale,
      backgroundColor: '#f7f4ef',
      style: {
        margin: '0',
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
    const drawW = captured.width * ratio
    const drawH = captured.height * ratio
    ctx.drawImage(
      captured,
      (targetWidth - drawW) / 2,
      (targetHeight - drawH) / 2,
      drawW,
      drawH,
    )

    const link = document.createElement('a')
    link.download = `${formatStamp()}.png`
    link.href = out.toDataURL('image/png')
    link.click()
  } catch (err) {
    console.error(err)
    await notice('保存失败', '生成图片时出错，请重试')
  } finally {
    unlock?.()
    editing.value = wasEditing
    saving.value = false
  }
}
</script>

<template>
  <div class="page">
    <header class="toolbar">
      <div class="toolbar-text">
        <p class="eyebrow">PRODUCT SHOWCASE</p>
      </div>
      <div class="toolbar-actions">
        <button
          type="button"
          class="ghost-btn"
          :disabled="historyBusy"
          @click="saveHistoryRecord"
        >
          保存记录
        </button>
        <button
          type="button"
          class="ghost-btn"
          :class="{ active: historyOpen }"
          @click="toggleHistory"
        >
          历史
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
          :disabled="saving"
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
          {{ saving ? '生成中…' : '一键保存 16:9 宣传图' }}
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
          <strong>历史记录</strong>
        </div>
        <button type="button" class="history-close" @click="historyOpen = false">关闭</button>
      </div>
      <p v-if="!histories.length" class="history-empty">还没有保存过记录。编辑完成后点「保存记录」。 </p>
      <ul v-else class="history-list">
        <li v-for="item in histories" :key="item.id" class="history-item">
          <button
            type="button"
            class="history-main"
            :disabled="historyBusy"
            @click="restoreHistory(item.id)"
          >
            <span class="history-name">{{ item.name }}</span>
            <span class="history-time">{{ formatTime(item.created_at) }}</span>
          </button>
          <div class="history-ops">
            <button type="button" :disabled="historyBusy" @click="renameHistory(item)">改名</button>
            <button type="button" class="danger" :disabled="historyBusy" @click="deleteHistory(item)">删除</button>
          </div>
        </li>
      </ul>
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

    <div class="stage-wrap">
      <div ref="boardRef" class="capture-shell">
        <ProductShowcase
          ref="showcaseRef"
          v-model:active-id="activeId"
          :editing="editing"
        />
      </div>
    </div>

    <p class="hint">
      {{
        editing
          ? '编辑模式：可改文字 · 可调字号 · 底部信息块可隐藏/显示 · 缩略图可传图/删除/新增'
          : '点击下方配色缩略图可切换主图 · 导出尺寸 1920×1080'
      }}
    </p>
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
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  max-width: 1200px;
  margin: 0 auto 22px;
}

.eyebrow {
  margin: 0;
  font-size: 11px;
  letter-spacing: 0.16em;
  color: #8a857e;
  font-weight: 600;
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
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
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
  width: min(380px, calc(100vw - 24px));
  box-sizing: border-box;
  padding: 22px 20px 24px;
  border-radius: 22px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.78), rgba(255, 255, 255, 0.4)),
    #f7f4ef;
  border: 1px solid rgba(255, 255, 255, 0.75);
  box-shadow: 0 24px 50px rgba(40, 30, 20, 0.16);
  transform: translateX(calc(100% + 24px));
  transition: transform 0.24s ease;
  overflow: auto;
}

.history-panel.open {
  transform: translateX(0);
}

.history-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 18px;
}

.history-kicker {
  margin: 0 0 4px;
  font-size: 10px;
  letter-spacing: 0.16em;
  color: #8a857e;
  font-weight: 700;
}

.history-head strong {
  font-size: 20px;
  font-weight: 800;
  letter-spacing: 0.02em;
}

.history-close,
.history-ops button {
  appearance: none;
  border: 1px solid #ddd4c8;
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
  margin: 40px 8px 0;
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
  gap: 10px;
}

.history-item {
  border: 1px solid #ece6dc;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.78);
  padding: 12px;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.history-item:hover {
  border-color: #d8cfc3;
  box-shadow: 0 8px 20px rgba(40, 30, 20, 0.06);
}

.history-main {
  appearance: none;
  width: 100%;
  border: none;
  background: transparent;
  text-align: left;
  cursor: pointer;
  padding: 0 0 8px;
}

.history-name {
  display: block;
  font-size: 14px;
  font-weight: 700;
  color: #1a1a1a;
}

.history-time {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: #8a857e;
}

.history-ops {
  display: flex;
  gap: 6px;
}

.history-ops .danger {
  color: #a02828;
  border-color: rgba(160, 40, 40, 0.35);
}

.edit-btn {
  appearance: none;
  border: 1px solid #c4b8a8;
  cursor: pointer;
  padding: 11px 16px;
  border-radius: 999px;
  background: #f7f4ef;
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

.capture-shell {
  border-radius: 18px;
}

.hint {
  max-width: 1200px;
  margin: 16px auto 0;
  text-align: center;
  font-size: 13px;
  color: #8a857e;
}

@media (max-width: 640px) {
  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .toolbar-actions {
    justify-content: stretch;
  }

  .edit-btn,
  .save-btn,
  .ghost-btn {
    flex: 1;
    justify-content: center;
  }
}
</style>
