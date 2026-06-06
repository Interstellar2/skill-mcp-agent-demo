import { ref, onUnmounted } from 'vue'
import cytoscape from 'cytoscape'

export function useCytoscape() {
  const cy = ref<cytoscape.Core | null>(null)

  function mount(factory: (container: HTMLElement) => cytoscape.Core, container: HTMLElement) {
    destroy()
    cy.value = factory(container)
  }

  function destroy() {
    if (cy.value) {
      cy.value.destroy()
      cy.value = null
    }
  }

  function fit(padding = 40) {
    cy.value?.fit(undefined, padding)
  }

  function applyLayout(name: string, options?: Record<string, unknown>) {
    cy.value?.layout({ name, ...options, animate: true, animationDuration: 400 } as any).run()
  }

  function highlightNode(stepIndex: number, status: string) {
    if (!cy.value) return
    const node = cy.value.getElementById(`step-${stepIndex}`)
    if (!node.length) return
    node.removeClass('node-running node-success node-error')
    if (status === 'pending' || status === 'running') node.addClass('node-running')
    else if (status === 'success') node.addClass('node-success')
    else if (status === 'error') node.addClass('node-error')
  }

  function highlightBatch(stepIndices: number[], active: boolean) {
    if (!cy.value) return
    stepIndices.forEach((idx) => {
      const node = cy.value!.getElementById(`step-${idx}`)
      if (!node.length) return
      if (active) node.addClass('batch-active')
      else node.removeClass('batch-active')
    })
  }

  function clearBatchHighlights() {
    if (!cy.value) return
    cy.value.nodes().removeClass('batch-active')
  }

  function highlightInvalidNodes(stepIndices: number[]) {
    if (!cy.value) return
    cy.value.nodes().removeClass('node-invalid')
    stepIndices.forEach((idx) => {
      const node = cy.value!.getElementById(`step-${idx}`)
      if (node.length) node.addClass('node-invalid')
    })
  }

  function clearInvalidHighlights() {
    if (!cy.value) return
    cy.value.nodes().removeClass('node-invalid')
  }

  onUnmounted(destroy)

  return {
    cy,
    mount,
    destroy,
    fit,
    applyLayout,
    highlightNode,
    highlightBatch,
    clearBatchHighlights,
    highlightInvalidNodes,
    clearInvalidHighlights,
  }
}
