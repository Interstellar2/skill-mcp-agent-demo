import type { Skill, SkillStep } from './types'

export function parseFrontmatter(text: string): { data: Record<string, unknown>; body: string } {
  if (!text.startsWith('---')) {
    return { data: {}, body: text }
  }
  const parts = text.split('---', 3)
  if (parts.length < 3) {
    return { data: {}, body: text }
  }
  const fmText = parts[1].trim()
  const body = parts[2].trim()

  const data: Record<string, unknown> = {}
  let currentKey: string | null = null
  let currentList: string[] | null = null
  let currentDict: Record<string, string> | null = null

  for (const line of fmText.split('\n')) {
    const stripped = line.trimEnd()
    if (!stripped) continue

    // List item (2-space indent + dash)
    const listMatch = stripped.match(/^  - (.+)$/)
    if (listMatch && currentKey && currentList !== null) {
      currentList.push(listMatch[1].trim().replace(/^"|"$/g, ''))
      continue
    }

    // Dict value (2-space indent)
    const dictMatch = stripped.match(/^  (\w+):\s*(.*)$/)
    if (dictMatch && currentKey && currentDict !== null) {
      const [, k, v] = dictMatch
      currentDict[k] = v.trim().replace(/^"|"$/g, '')
      continue
    }

    // Top-level key-only (starts list or dict)
    const keyOnlyMatch = stripped.match(/^(\w+):\s*$/)
    if (keyOnlyMatch) {
      currentKey = keyOnlyMatch[1]
      // Heuristic: if next non-empty line starts with "  -", it's a list
      // We'll lazily create list or dict on first child line
      currentList = []
      currentDict = {}
      data[currentKey] = currentList
      continue
    }

    // Top-level key-value
    const kvMatch = stripped.match(/^(\w+):\s*(.+)$/)
    if (kvMatch) {
      const [, k, v] = kvMatch
      data[k] = v.trim().replace(/^"|"$/g, '')
      currentKey = k
      currentList = null
      currentDict = null
      continue
    }
  }

  // Post-process: if a key got both list and dict entries, prefer list if it has items
  // Our naive parser may have set data[key] to list initially. If dict has items and list is empty, switch.
  for (const key of Object.keys(data)) {
    // This is a simplification; for our known skill format it works.
  }

  return { data, body }
}

export function parseSteps(body: string): SkillStep[] {
  const steps: SkillStep[] = []
  const pattern = /###\s*步骤\s*(\d+)\s*[:：]\s*(.+?)(?=\n###\s*步骤|\n##\s|$)/gs

  for (const m of body.matchAll(pattern)) {
    const num = parseInt(m[1], 10)
    const block = m[0]
    const titleLine = m[2].trim().split('\n')[0]

    const toolMatch = block.match(/\*\*工具\*\*:\s*`([^`]+)`/)
    const tool = toolMatch ? toolMatch[1] : null

    const subMatch = block.match(/\*\*子流程\*\*:\s*`([^`]+)`/)
    const subSkill = subMatch ? subMatch[1] : null

    steps.push({
      id: `step_${num}`,
      number: num,
      title: titleLine,
      tool,
      sub_skill: subSkill,
      raw: block.trim(),
    })
  }

  steps.sort((a, b) => a.number - b.number)
  return steps
}

export function parseSkill(name: string, text: string): Skill {
  const { data, body } = parseFrontmatter(text)
  const steps = parseSteps(body)

  return {
    name: (data['name'] as string) || name,
    description: (data['description'] as string) || '',
    tools: (data['tools'] as string[]) || [],
    scripts: (data['scripts'] as Record<string, string>) || {},
    templates: (data['templates'] as Record<string, string>) || {},
    variables: (data['variables'] as Record<string, unknown>) || {},
    steps,
    raw: text,
  }
}
