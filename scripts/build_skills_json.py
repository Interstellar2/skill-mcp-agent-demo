#!/usr/bin/env python3
"""Parse skills directory and generate skills_data.json for frontend."""

import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
SKILLS_DIR = PROJECT_ROOT / "skills"
OUTPUT = (PROJECT_ROOT / "frontend" / "public" / "skills_data.json").resolve()


def parse_frontmatter(text: str):
    """Parse YAML-like frontmatter from markdown."""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    fm_text = parts[1].strip()
    body = parts[2].strip()

    data = {}
    current_key = None
    current_list = None
    current_dict = None

    for line in fm_text.splitlines():
        stripped = line.rstrip()
        if not stripped:
            continue

        # List item
        m = re.match(r"^  - (.+)$", stripped)
        if m and current_key and current_list is not None:
            current_list.append(m.group(1).strip().strip('"'))
            continue

        # Dict value (2-space indent)
        m = re.match(r"^  (\w+):\s*(.*)$", stripped)
        if m and current_key and current_dict is not None:
            k, v = m.group(1), m.group(2).strip().strip('"')
            current_dict[k] = v
            continue

        # Top-level key with list
        m = re.match(r"^(\w+):$", stripped)
        if m:
            current_key = m.group(1)
            current_list = []
            current_dict = None
            data[current_key] = current_list
            continue

        # Top-level key with dict
        m = re.match(r"^(\w+):$", stripped)
        if m and current_key and current_dict is not None:
            # nested dict not expected at top-level for our format
            pass

        # Top-level key-value
        m = re.match(r"^(\w+):\s*(.*)$", stripped)
        if m:
            k, v = m.group(1), m.group(2).strip().strip('"')
            if v == "":
                current_key = k
                current_dict = {}
                current_list = None
                data[k] = current_dict
            else:
                data[k] = v
                current_key = k
                current_list = None
                current_dict = None
            continue

    return data, body


def parse_steps(body: str):
    """Extract numbered steps from markdown body."""
    steps = []
    # Split by step headers
    pattern = r"###\s*步骤\s*(\d+)\s*[:：]\s*(.+?)(?=\n###\s*步骤|\n##\s|$)"
    for m in re.finditer(pattern, body, re.DOTALL):
        num = int(m.group(1))
        title = m.group(2).strip().split('\n')[0].strip()
        content = m.group(0)

        # Extract tool
        tool_match = re.search(r"\*\*工具\*\*:\s*`([^`]+)`", content)
        tool = tool_match.group(1) if tool_match else None

        # Extract sub-skill
        sub_match = re.search(r"\*\*子流程\*\*:\s*`([^`]+)`", content)
        sub_skill = sub_match.group(1) if sub_match else None

        steps.append({
            "id": f"step_{num}",
            "number": num,
            "title": title,
            "tool": tool,
            "sub_skill": sub_skill,
            "raw": content.strip(),
        })

    # Sort by number just in case
    steps.sort(key=lambda x: x["number"])
    return steps


def parse_skill(skill_dir: Path):
    md_file = skill_dir / "SKILL.md"
    if not md_file.exists():
        return None

    text = md_file.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)
    steps = parse_steps(body)

    return {
        "name": fm.get("name", skill_dir.name),
        "description": fm.get("description", ""),
        "tools": fm.get("tools", []),
        "scripts": fm.get("scripts", {}),
        "templates": fm.get("templates", {}),
        "variables": fm.get("variables", {}),
        "steps": steps,
        "raw": text,
    }


def main():
    skills = []
    for item in sorted(SKILLS_DIR.iterdir()):
        if item.is_dir():
            skill = parse_skill(item)
            if skill:
                skills.append(skill)

    OUTPUT.write_text(json.dumps(skills, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Generated {OUTPUT} with {len(skills)} skills.")


if __name__ == "__main__":
    main()
