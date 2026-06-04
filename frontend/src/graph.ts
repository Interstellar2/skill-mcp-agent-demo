import cytoscape from 'cytoscape'
import type { Skill } from './types'
import { getNodeColor, getNodeLabel, createGraphStyle } from './graph-styles'
import { bindGraphEvents, createResizeObserver } from './graph-events'

export function renderGraph(container: HTMLElement, skill: Skill): cytoscape.Core {
  const nodes = skill.steps.map((step) => ({
    data: {
      id: step.id,
      label: getNodeLabel(step),
      color: getNodeColor(step),
      tool: step.tool || step.sub_skill || 'none',
    },
  }))

  const edges: cytoscape.ElementDefinition[] = []
  for (let i = 0; i < skill.steps.length - 1; i++) {
    edges.push({
      data: {
        id: `edge_${i}`,
        source: skill.steps[i].id,
        target: skill.steps[i + 1].id,
      },
    })
  }

  const cy = cytoscape({
    container,
    elements: [...nodes, ...edges],
    style: createGraphStyle() as any,
    layout: {
      name: 'breadthfirst',
      directed: true,
      padding: 40,
      spacingFactor: 1.4,
      nodeDimensionsIncludeLabels: true,
      animate: true,
      animationDuration: 400,
    } as cytoscape.LayoutOptions,
    wheelSensitivity: 0.25,
    minZoom: 0.2,
    maxZoom: 2.5,
  })

  bindGraphEvents(cy)

  const resizeObserver = createResizeObserver(cy, container)

  // Store observer for cleanup
  ;(cy as any)._resizeObserver = resizeObserver

  return cy
}
