import cytoscape from 'cytoscape'
import type { Skill } from '../types'
import { getNodeColor, getNodeLabel, createGraphStyle } from './styles'

export function buildElements(skill: Skill): cytoscape.ElementDefinition[] {
  const nodes = skill.steps.map((step) => ({
    data: {
      id: `step-${step.number}`,
      label: getNodeLabel(step),
      color: getNodeColor(step),
      tool: step.tool || step.sub_skill || 'none',
      stepIndex: step.number,
    },
  }))

  const edges: cytoscape.ElementDefinition[] = []
  for (let i = 0; i < skill.steps.length - 1; i++) {
    edges.push({
      data: {
        id: `edge_${i}`,
        source: `step-${skill.steps[i].number}`,
        target: `step-${skill.steps[i + 1].number}`,
      },
    })
  }

  return [...nodes, ...edges]
}

export function createGraph(
  container: HTMLElement,
  elements: cytoscape.ElementDefinition[],
  layoutName: string = 'breadthfirst',
): cytoscape.Core {
  const cy = cytoscape({
    container,
    elements,
    style: createGraphStyle() as any,
    layout: {
      name: layoutName,
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

  // Hover effects
  cy.on('mouseover', 'node', (evt) => {
    evt.target.addClass('hover')
  })
  cy.on('mouseout', 'node', (evt) => {
    evt.target.removeClass('hover')
  })

  // Click node to center
  cy.on('tap', 'node', (evt) => {
    cy.animate({
      fit: { eles: evt.target, padding: 80 },
      duration: 300,
    })
  })

  // Double-click blank area to reset fit
  cy.on('tap', (evt) => {
    if (evt.target === cy) {
      cy.animate({
        fit: { eles: cy.elements(), padding: 40 },
        duration: 350,
      })
    }
  })

  // Auto-fit on initial layout
  cy.one('layoutstop', () => {
    cy.fit(cy.elements(), 40)
  })

  return cy
}
