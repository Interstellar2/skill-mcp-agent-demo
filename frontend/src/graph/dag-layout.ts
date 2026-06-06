import type { Skill } from '../types'

export function buildDagElements(skill: Skill): cytoscape.ElementDefinition[] {
  const steps = skill.steps
  const nodes = steps.map((step) => ({
    data: {
      id: `step-${step.number}`,
      label: `${step.number}. ${step.title}`,
      color: step.sub_skill ? '#F8B195' : step.tool ? '#B5EAD7' : '#F0F0F0',
      tool: step.tool || step.sub_skill || 'none',
      stepIndex: step.number,
    },
  }))

  const edges: cytoscape.ElementDefinition[] = []

  // Build group mapping
  const groupLastStep: Record<string, number> = {}
  for (const step of steps) {
    const gid = (step as any).parallel_group_id as string | undefined
    if (gid) {
      groupLastStep[gid] = step.number
    }
  }

  // Build edges based on dependencies
  for (let i = 0; i < steps.length; i++) {
    const step = steps[i]
    const idx = step.number
    const gid = (step as any).parallel_group_id as string | undefined
    const explicitDeps = ((step as any).depends_on as string[] | undefined) || []

    if (explicitDeps.length > 0) {
      for (const dep of explicitDeps) {
        if (groupLastStep[dep]) {
          edges.push({
            data: {
              id: `edge_${idx}_dep_${dep}`,
              source: `step-${groupLastStep[dep]}`,
              target: `step-${idx}`,
            },
          })
        } else {
          const depIdx = parseInt(dep, 10)
          if (!isNaN(depIdx) && depIdx < idx) {
            edges.push({
              data: {
                id: `edge_${idx}_dep_${depIdx}`,
                source: `step-${depIdx}`,
                target: `step-${idx}`,
              },
            })
          }
        }
      }
    } else if (gid) {
      if (i > 0) {
        const prevGid = (steps[i - 1] as any).parallel_group_id as string | undefined
        if (prevGid !== gid) {
          edges.push({
            data: {
              id: `edge_${idx}_seq`,
              source: `step-${steps[i - 1].number}`,
              target: `step-${idx}`,
            },
          })
        }
      }
    } else {
      if (i > 0) {
        edges.push({
          data: {
            id: `edge_${idx}_seq`,
            source: `step-${steps[i - 1].number}`,
            target: `step-${idx}`,
          },
        })
      }
    }
  }

  return [...nodes, ...edges]
}
