import cytoscape from 'cytoscape'
import { Marked } from 'marked'
import type { Skill } from './types'
import { renderGraph } from './graph'

const marked = new Marked({ breaks: true })

let currentCy: cytoscape.Core | null = null

export async function initApp() {
  const skillListEl = document.getElementById('skill-list')!
  const emptyStateEl = document.getElementById('empty-state')!
  const contentAreaEl = document.getElementById('content-area')!

  let skills: Skill[] = []

  try {
    const res = await fetch('./skills_data.json')
    if (!res.ok) throw new Error('Failed to load skills_data.json')
    skills = (await res.json()) as Skill[]
  } catch {
    skillListEl.innerHTML = '<li class="error">加载 Skill 数据失败，请确保 skills_data.json 存在。</li>'
    return
  }

  // Render skill list
  skills.forEach((skill) => {
    const li = document.createElement('li')
    li.className = 'skill-item'
    li.dataset.name = skill.name

    const title = document.createElement('div')
    title.className = 'skill-item-title'
    title.textContent = skill.name

    const desc = document.createElement('div')
    desc.className = 'skill-item-desc'
    desc.textContent = skill.description

    const meta = document.createElement('div')
    meta.className = 'skill-item-meta'
    meta.textContent = `${skill.steps.length} 步骤 · ${skill.tools.length} 工具`

    li.appendChild(title)
    li.appendChild(desc)
    li.appendChild(meta)

    li.addEventListener('click', () => {
      document.querySelectorAll('.skill-item').forEach((el) => el.classList.remove('active'))
      li.classList.add('active')
      loadSkill(skill)
      emptyStateEl.classList.add('hidden')
      contentAreaEl.classList.remove('hidden')
    })

    skillListEl.appendChild(li)
  })

  // Auto-select first skill
  if (skills.length > 0) {
    skillListEl.querySelector('.skill-item')?.dispatchEvent(new Event('click'))
  }
}

function loadSkill(skill: Skill) {
  const contentAreaEl = document.getElementById('content-area')!
  const titleEl = document.getElementById('skill-title')!
  const toolsEl = document.getElementById('skill-tools')!
  const markdownBodyEl = document.getElementById('markdown-body')!
  const cyContainer = document.getElementById('cy')!

  titleEl.textContent = skill.name

  toolsEl.innerHTML = skill.tools
    .map((t) => `<span class="tool-tag">${t}</span>`)
    .join('')

  // Render markdown (strip frontmatter)
  const displayMarkdown = skill.raw.replace(/^---[\s\S]*?---\n*/, '').trim()
  const mdHtml = marked.parse(displayMarkdown) as string
  markdownBodyEl.innerHTML = mdHtml

  // Render graph
  if (currentCy) {
    const observer = (currentCy as any)._resizeObserver
    if (observer) observer.disconnect()
    currentCy.destroy()
  }
  currentCy = renderGraph(cyContainer, skill)

  // Fade in content with subtle animation
  contentAreaEl.animate([
    { opacity: 0.6, transform: 'translateY(6px)' },
    { opacity: 1, transform: 'translateY(0)' }
  ], {
    duration: 250,
    easing: 'ease-out'
  })
}
