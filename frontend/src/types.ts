export interface SkillStep {
  id: string;
  number: number;
  title: string;
  tool: string | null;
  sub_skill: string | null;
  raw: string;
}

export interface Skill {
  name: string;
  description: string;
  tools: string[];
  scripts: Record<string, string>;
  templates: Record<string, string>;
  variables: Record<string, unknown>;
  steps: SkillStep[];
  raw: string;
}
