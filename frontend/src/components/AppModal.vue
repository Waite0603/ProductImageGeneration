<script setup>
import { nextTick, ref, watch } from 'vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  title: { type: String, default: '' },
  message: { type: String, default: '' },
  input: { type: Boolean, default: false },
  inputValue: { type: String, default: '' },
  inputPlaceholder: { type: String, default: '' },
  confirmText: { type: String, default: '确定' },
  cancelText: { type: String, default: '取消' },
  hideCancel: { type: Boolean, default: false },
  danger: { type: Boolean, default: false },
})

const emit = defineEmits(['close', 'confirm', 'update:inputValue'])

const field = ref(null)
const draft = ref(props.inputValue)

watch(
  () => [props.open, props.inputValue],
  ([open]) => {
    if (!open) return
    draft.value = props.inputValue
    nextTick(() => {
      field.value?.focus()
      field.value?.select?.()
    })
  },
)

function onKeydown(e) {
  if (e.key === 'Escape') {
    e.preventDefault()
    emit('close')
  }
  if (e.key === 'Enter' && !e.isComposing) {
    e.preventDefault()
    submit()
  }
}

function submit() {
  if (props.input && !draft.value.trim()) return
  emit('confirm', props.input ? draft.value.trim() : true)
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="modal-mask"
      @click.self="emit('close')"
      @keydown="onKeydown"
    >
      <div
        class="modal-card"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="title ? 'app-modal-title' : undefined"
      >
        <header v-if="title" class="modal-head">
          <h3 id="app-modal-title">{{ title }}</h3>
        </header>
        <p v-if="message" class="modal-msg">{{ message }}</p>
        <input
          v-if="input"
          ref="field"
          v-model="draft"
          class="modal-input"
          type="text"
          :placeholder="inputPlaceholder"
          maxlength="200"
        />
        <footer class="modal-foot">
          <button
            v-if="!hideCancel"
            type="button"
            class="modal-btn ghost"
            @click="emit('close')"
          >
            {{ cancelText }}
          </button>
          <button
            type="button"
            class="modal-btn"
            :class="danger ? 'danger' : 'primary'"
            :disabled="input && !draft.trim()"
            @click="submit"
          >
            {{ confirmText }}
          </button>
        </footer>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.modal-mask {
  position: fixed;
  inset: 0;
  z-index: 10050;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  padding-bottom: max(16px, env(safe-area-inset-bottom));
  overflow: auto;
  background: rgba(28, 22, 16, 0.48);
  backdrop-filter: blur(8px);
}

.modal-card {
  width: min(420px, 100%);
  max-height: calc(100dvh - 32px);
  overflow: auto;
  padding: 22px 22px 18px;
  border-radius: 20px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.72), rgba(255, 255, 255, 0.38)),
    #f7f4ef;
  border: 1px solid rgba(255, 255, 255, 0.7);
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.8) inset,
    0 28px 60px rgba(40, 30, 20, 0.22);
}

.modal-head h3 {
  margin: 0;
  font-size: 17px;
  font-weight: 800;
  letter-spacing: 0.02em;
  color: #1a1a1a;
}

.modal-msg {
  margin: 10px 0 0;
  font-size: 13px;
  line-height: 1.65;
  color: #6f6a63;
}

.modal-input {
  display: block;
  width: 100%;
  margin-top: 14px;
  padding: 11px 12px;
  border: 1px solid #ddd4c8;
  border-radius: 12px;
  background: #fff;
  color: #1a1a1a;
  font-size: 14px;
  font-weight: 600;
  outline: none;
}

.modal-input:focus {
  border-color: #c45c4a;
  box-shadow: 0 0 0 3px rgba(196, 92, 74, 0.16);
}

.modal-foot {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 18px;
}

.modal-btn {
  appearance: none;
  border: none;
  border-radius: 999px;
  padding: 10px 16px;
  min-width: 76px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.modal-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.modal-btn.ghost {
  background: #efeae3;
  color: #1a1a1a;
}

.modal-btn.ghost:hover {
  background: #e7e0d6;
}

.modal-btn.primary {
  background: #1f1f1f;
  color: #fff;
}

.modal-btn.primary:hover:not(:disabled) {
  background: #333;
}

.modal-btn.danger {
  background: #c45c4a;
  color: #fff;
}

.modal-btn.danger:hover:not(:disabled) {
  background: #b04f3e;
}
</style>
