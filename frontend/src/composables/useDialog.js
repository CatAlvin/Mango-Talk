import { nextTick, onBeforeUnmount, ref, watch } from 'vue'

export function useDialog(open, close) {
  const panelRef = ref(null)
  let previousFocus
  function keydown(event) {
    if (!open.value) return
    if (event.key === 'Escape') { event.preventDefault(); close(); return }
    if (event.key !== 'Tab') return
    const controls = [...(panelRef.value?.querySelectorAll('button:not(:disabled), input:not(:disabled), textarea:not(:disabled), [tabindex="0"]') || [])]
    const first = controls[0]; const last = controls.at(-1)
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus() }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
  }
  watch(open, async (value) => {
    if (value) {
      previousFocus = document.activeElement
      document.addEventListener('keydown', keydown)
      await nextTick()
      panelRef.value?.querySelector('input')?.focus()
    } else { document.removeEventListener('keydown', keydown); previousFocus?.focus() }
  })
  onBeforeUnmount(() => document.removeEventListener('keydown', keydown))
  return { panelRef }
}
