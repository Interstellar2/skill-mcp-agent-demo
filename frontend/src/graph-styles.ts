import type { SkillStep } from './types'

export const TOOL_COLORS: Record<string, string> = {
  cut_ingredient: '#FF9AA2',
  crack_egg: '#FFB7B2',
  heat_pan: '#FFDAC1',
  stir_fry: '#E2F0CB',
  season: '#B5EAD7',
  plate: '#C7CEEA',
  default: '#F0F0F0',
}

export function getNodeColor(step: SkillStep): string {
  if (step.sub_skill) return '#F8B195'
  if (step.tool && TOOL_COLORS[step.tool]) return TOOL_COLORS[step.tool]
  return TOOL_COLORS.default
}

export function getNodeLabel(step: SkillStep): string {
  return `${step.number}. ${step.title}`
}

export function createGraphStyle() {
  return [
    {
      selector: 'node',
      style: {
        'background-color': 'data(color)',
        'label': 'data(label)',
        'width': 'label',
        'height': 44,
        'padding': 14,
        'shape': 'round-rectangle',
        'text-valign': 'center',
        'text-halign': 'center',
        'font-size': 12.5,
        'font-family': 'system-ui, -apple-system, sans-serif',
        'font-weight': 600,
        'color': '#1e293b',
        'border-width': 2.5,
        'border-color': '#fff',
        'border-opacity': 0.9,
        'text-wrap': 'wrap',
        'text-max-width': 200,
        'shadow-blur': 8,
        'shadow-color': 'rgba(15, 23, 42, 0.08)',
        'shadow-offset-y': 3,
        'transition-property': 'background-color, border-color, width, height, shadow-blur',
        'transition-duration': 0.25,
      },
    },
    {
      selector: 'edge',
      style: {
        'width': 2,
        'line-color': '#cbd5e1',
        'target-arrow-color': '#94a3b8',
        'target-arrow-shape': 'triangle',
        'curve-style': 'bezier',
        'arrow-scale': 1.1,
      },
    },
    {
      selector: ':selected',
      style: {
        'border-width': 3,
        'border-color': '#3b82f6',
        'background-color': '#eff6ff',
        'shadow-blur': 12,
        'shadow-color': 'rgba(59, 130, 246, 0.2)',
      },
    },
    {
      selector: 'node.hover',
      style: {
        'border-color': '#3b82f6',
        'border-width': 3,
        'shadow-blur': 12,
        'shadow-color': 'rgba(59, 130, 246, 0.15)',
      },
    },
  ]
}
