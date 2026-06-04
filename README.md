# Kitchen SOP Demo - Skill + MCP + LangChain 演示项目

一个展示**结构化 Skill 管理**、**MCP 工具协议**、**LangChain Agent**、**多种执行编排模式**与**可视化 Web UI** 如何协同工作的演示项目。

用三道中餐菜谱（番茄炒蛋、宫保鸡丁、可乐鸡翅）作为示例，让 LLM 或直接按 SOP 流程调用"厨房工具"完成做菜，支持**计划-执行分离**、**人在回路**、**并行执行**与**断点续作/回滚**，并通过 Web UI 可视化查看 Skill 内容与执行流程。

---

## 项目架构

```
┌─────────────────────────────────────────────────────────────┐
│                     Skill 层（流程定义）                        │
│  skills/tomato_egg/SKILL.md          # Markdown + YAML        │
│  skills/kung_pao_chicken/SKILL.md    # 标准操作流程            │
│  skills/kung_pao_chicken/scripts/    # 执行钩子脚本            │
│  skills/kung_pao_chicken/reference/  # 参考资料                │
│  skills/kung_pao_chicken/templates/  # 输出模板                │
└─────────────────────────────────────────────────────────────┘
                              ↓ 加载 / 解析
┌─────────────────────────────────────────────────────────────┐
│                   Skill Manager（技能管理）                    │
│  backend/kitchen_sop/skill_manager.py    ──  扫描目录、解析      │
│  backend/kitchen_sop/sop_parser.py       ──  提取工具调用步骤   │
│  backend/kitchen_sop/script_runner.py    ──  执行 pre/post 脚本│
│  backend/kitchen_sop/reference_loader.py ──  加载参考文档      │
│  backend/kitchen_sop/template_engine.py  ──  模板渲染          │
└─────────────────────────────────────────────────────────────┘
                              ↓ 调用
┌─────────────────────────────────────────────────────────────┐
│                  执行引擎层（6 种模式 + 共享基类）               │
│  base.py              ──  SkillExecutorContext + 通用工具封装  │
│  demo.py              ──  顺序执行（无需 API Key）              │
│  agent.py             ──  LLM 自主决策                          │
│  plan_then_execute.py ──  计划-执行分离                         │
│  hitl.py              ──  人在回路（Human-in-the-Loop）         │
│  parallel.py          ──  DAG 拓扑并行执行                      │
│  resumable.py         ──  检查点 + 自动断电续作                  │
│  resume.py            ──  从检查点恢复执行                      │
│  rollback.py          ──  回滚到指定步骤重试                    │
└─────────────────────────────────────────────────────────────┘
                              ↓ JSON-RPC (stdio)
┌─────────────────────────────────────────────────────────────┐
│                      MCP 工具层（执行）                        │
│  backend/mcp_server.py  ──  cut_ingredient / stir_fry ...    │
└─────────────────────────────────────────────────────────────┘
                              ↓ 构建产物
┌─────────────────────────────────────────────────────────────┐
│                     Web UI 可视化层                            │
│  frontend/src/               ──  Vite + TypeScript 前端        │
│  frontend/public/skills_data.json ──  Skill 数据（自动生成）   │
│  scripts/build_skills_json.py     ──  构建脚本                │
└─────────────────────────────────────────────────────────────┘
```

| 层级 | 职责 | 类比 |
|---|---|---|
| **Skill** | 定义"做什么"（SOP 流程、工具映射、参数） | 菜谱 |
| **Skill Manager / Parser** | 加载、解析、管理多个 Skill | 菜谱架 |
| **Executors** | 决定"怎么做"（顺序/LLM/并行/人在回路等） | 厨师大脑 |
| **MCP Server** | 实际"动手做"（工具实现） | 厨房设备 |
| **Web UI** | 可视化展示 Skill 内容与流程 | 电子菜谱屏 |

---

## 环境准备

### 1. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

依赖包括：`langchain`、`mcp`、`python-dotenv`、`pyyaml` 等。

### 2. 安装前端依赖

```bash
cd frontend
npm install
```

### 3. 配置环境变量（可选，仅 Agent 模式需要）

```bash
cp .env.example .env
# 编辑 .env 填入你的 API Key
```

`.env` 示例：
```bash
OPENAI_API_KEY=sk-xxxxxxxx
# OPENAI_BASE_URL=https://api.openai.com/v1   # 第三方兼容服务时填写
# MODEL=gpt-4o-mini                           # 默认模型
```

---

## 快速开始

### Demo 模式（推荐首次体验）

无需 API Key，直接按 SOP 步骤顺序调用工具：

```bash
# 番茄炒蛋（8 步）
python backend/main.py --demo --skill tomato_egg

# 宫保鸡丁（10 步，流程更复杂）
python backend/main.py --demo --skill kung_pao_chicken

# 可乐鸡翅（7 步）
python backend/main.py --demo --skill cola_chicken_wings
```

### 传入变量覆盖默认值

Skill 支持在 frontmatter 中定义变量，执行时通过 `--var` 传入：

```bash
# 番茄炒蛋用 5 个鸡蛋（默认 3 个）
python backend/main.py --demo --skill tomato_egg --var egg_count=5
```

### Agent 模式（需要 LLM）

让大模型根据 SOP 自主决策调用工具：

```bash
# 使用默认模型（gpt-4o-mini）
python backend/main.py --agent --skill tomato_egg

# 指定模型
python backend/main.py --agent --skill kung_pao_chicken --model gpt-4o
```

> 如果没有配置 `OPENAI_API_KEY`，会自动回退到 Demo 模式。

### Plan-then-Execute 模式（需要 LLM）

先由 LLM 生成结构化执行计划，再严格按计划顺序执行，执行阶段不依赖 LLM：

```bash
python backend/main.py --plan-then-execute --skill tomato_egg
```

### Human-in-the-Loop 模式

在关键步骤执行前暂停，等待人工确认（支持确认/拒绝/修改参数）：

```bash
python backend/main.py --hitl --skill tomato_egg
```

> 需要在 `SKILL.md` 的 frontmatter 中配置 `human_in_the_loop` 规则。

### 并行执行模式

解析 SOP 中的 `[parallel-group]` 和 `[depends-on]` 标记，将无依赖步骤分组并行执行：

```bash
python backend/main.py --parallel --skill tomato_egg
```

### 断电续作 / 回滚

使用 `--resumable` 执行时自动保存检查点，支持从断点恢复或回滚到指定步骤重试：

```bash
# 带检查点的顺序执行
python backend/main.py --resumable --skill tomato_egg

# 从断点恢复（继续执行未完成的步骤）
python backend/main.py --resume <run_id>

# 回滚到步骤 3 重新执行
python backend/main.py --rollback <run_id> --to-step 3
```

### Web UI 可视化

启动前端开发服务器，在浏览器中查看 Skill 列表、SOP 内容与流程图：

```bash
cd frontend
npm run dev
```

打开 http://localhost:5173/，左侧选择 Skill，右侧查看 Markdown 内容与步骤流程图。

> `npm run dev` 会自动调用 `scripts/build_skills_json.py` 生成最新数据。

### 查看执行历史与回放

每次执行会自动记录到 `runs/` 目录：

```bash
# 列出最近 20 次执行
python backend/main.py --list-runs

# 回放某次执行（不调用真实工具）
python backend/main.py --replay abc123
```

---

## 六种执行模式对比

| 特性 | Demo | Agent | Plan-then-Execute | HITL | Parallel | Resumable |
|---|---|---|---|---|---|---|
| 需要 API Key | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ |
| 执行方式 | 严格顺序 | LLM 自主决策 | 计划→顺序执行 | 顺序+人工确认 | DAG 拓扑并行 | 顺序+自动检查点 |
| 适用场景 | 确定性流程 | 灵活决策 | 可控的 LLM 辅助 | 关键步骤需审批 | 可并行步骤 | 长流程防中断 |
| 可解释性 | 完全透明 | 依赖 LLM | 计划透明 | 完全透明 | 完全透明 | 完全透明 |
| 执行时间 | 秒级 | 模型依赖 | 模型+秒级 | 人工依赖 | 秒级 | 秒级 |

---

## 项目结构

```
.
├── backend/                         # Python 后端
│   ├── main.py                      # 命令行入口（委托 cli / commands / router）
│   ├── cli.py                       # 参数解析器（argparse）
│   ├── commands.py                  # 查询类命令（--list-runs / --replay）
│   ├── router.py                    # 执行路由（模式解析 + executor 分发）
│   ├── mcp_server.py                # MCP 厨房工具服务器（独立进程）
│   ├── requirements.txt             # Python 依赖
│   └── kitchen_sop/                 # 核心包
│       ├── __init__.py
│       ├── config.py                # 环境变量加载、项目根目录常量
│       ├── logging_utils.py         # 统一日志配置
│       ├── skill_manager.py         # Skill 扫描与解析（目录化结构）
│       ├── sop_parser.py            # SOP Markdown 提取工具调用步骤（支持子流程内联）
│       ├── template_engine.py       # 变量模板渲染（{{var}} 替换）
│       ├── script_runner.py         # Skill 脚本执行引擎（pre/post hooks）
│       ├── reference_loader.py      # 参考资料加载与格式化
│       ├── mcp_client.py            # MCP 客户端连接管理
│       ├── tracker/                 # 执行观测与审计
│       │   ├── __init__.py
│       │   ├── models.py            # RunRecord / StepRecord / ExecutionPlan / Checkpoint 数据模型
│       │   └── core.py              # RunTracker 上下文管理器与持久化
│       ├── checkpoint.py            # 检查点管理器（CheckpointManager）
│       └── executors/               # 执行器（共享基类 + 6 种模式）
│           ├── __init__.py
│           ├── base.py              # SkillExecutorContext + execute_step 通用封装
│           ├── demo.py              # Demo 模式：按 SOP 顺序执行
│           ├── agent.py             # Agent 模式：LangChain + LLM 自主决策
│           ├── plan_then_execute.py # Plan-then-Execute：计划-执行分离
│           ├── hitl.py              # Human-in-the-Loop：人在回路
│           ├── parallel.py          # Parallel：DAG 拓扑并行执行
│           ├── resumable.py         # Resumable：检查点 + 自动断电续作
│           ├── resume.py            # Resume：从检查点恢复执行
│           └── rollback.py          # Rollback：回滚到指定步骤重试
│
├── frontend/                        # Vite + TypeScript 前端
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── src/
│   │   ├── main.ts                  # 入口
│   │   ├── app.ts                   # 应用逻辑（Skill 列表、Markdown 渲染）
│   │   ├── graph.ts                 # Cytoscape 流程图主函数
│   │   ├── graph-styles.ts          # Cytoscape 样式配置（节点颜色、边样式）
│   │   ├── graph-events.ts          # Cytoscape 事件绑定（hover、点击、resize）
│   │   ├── parser.ts                # Markdown / frontmatter 解析器
│   │   ├── types.ts                 # 类型定义
│   │   └── style.css                # 样式
│   └── public/
│       └── skills_data.json         # 构建产物：Skill 数据（自动生成）
│
├── scripts/
│   └── build_skills_json.py         # 构建脚本：skills/ → frontend/public/skills_data.json
│
├── skills/                          # Skill 目录（每个 Skill 一个子目录）
│   ├── tomato_egg/                  # 番茄炒蛋（带变量 + scripts + reference）
│   │   ├── SKILL.md
│   │   ├── scripts/
│   │   │   └── pre_check.py
│   │   ├── reference/
│   │   │   └── egg_tips.md
│   │   └── templates/
│   │       └── dish_report.md
│   ├── kung_pao_chicken/            # 宫保鸡丁（带子流程 + scripts + reference）
│   │   ├── SKILL.md
│   │   ├── scripts/
│   │   │   ├── pre_check.py
│   │   │   └── post_cleanup.py
│   │   ├── reference/
│   │   │   └── knife_skills.md
│   │   └── templates/
│   │       └── dish_report.md
│   ├── cola_chicken_wings/          # 可乐鸡翅（带 scripts + reference）
│   │   ├── SKILL.md
│   │   ├── scripts/
│   │   │   └── pre_check.py
│   │   ├── reference/
│   │   │   └── cola_tips.md
│   │   └── templates/
│   │       └── dish_report.md
│   └── marinate_meat/               # 通用腌制子流程（可被其他 Skill 引用）
│       └── SKILL.md
│
├── logs/                            # 运行后自动生成
│   ├── YYYY-MM-DD.log               # agent 侧日志
│   └── mcp_server_YYYY-MM-DD.log    # MCP 服务端日志
│
├── runs/                            # 执行记录（自动生成，每条一个 JSON）
│   └── checkpoints/                 # 检查点文件（Resumable 模式自动生成）
├── .env.example                     # 环境变量模板
└── README.md                        # 本文件
```

---

## Skill 目录结构

每个 Skill 是一个**目录**，主流程定义在 `SKILL.md` 中，支持 `scripts/`、`reference/`、`templates/` 三个子目录：

```
skills/
└── kung_pao_chicken/
    ├── SKILL.md              # 主 SOP（YAML frontmatter + Markdown）
    ├── scripts/              # 执行钩子脚本（可选）
    │   ├── pre_check.py      # 执行前运行
    │   └── post_cleanup.py   # 执行后运行
    ├── reference/            # 参考资料（可选）
    │   └── knife_skills.md
    └── templates/            # 输出模板（可选）
        └── dish_report.md
```

### SKILL.md 格式

`SKILL.md` 采用 **YAML frontmatter + Markdown** 格式：

```markdown
---
name: kung_pao_chicken
description: 宫保鸡丁标准操作流程
scripts:
  pre: scripts/pre_check.py
  post: scripts/post_cleanup.py
templates:
  report: templates/dish_report.md
variables:
  egg_count:
    type: int
    default: 3
tools:
  - cut_ingredient
  - stir_fry
  - season
  - plate
---

# 宫保鸡丁 SOP

## 操作步骤

### 步骤 1: 处理鸡肉
**工具**: `cut_ingredient`
**参数**:
- ingredient: "鸡腿肉"
- method: "去骨切丁"

### 步骤 2: 腌制鸡肉
**子流程**: `marinate_meat`
```

**解析规则**：
- `---` 包围的 YAML 是元数据（名称、描述、变量定义、工具列表、scripts/templates 引用）
- `### 步骤 N` 标题下查找 `**工具**: ` 标记
- `**参数**:` 下的 `- key: value` 会被提取为工具调用参数
- 支持自动类型转换：`true`/`false` → bool，`30` → int
- 支持模板变量：`{{variable_name}}` 会被执行时传入的值替换

**并行执行标记**（Parallel 模式专用）：
```markdown
**工具**: `cut_ingredient` [parallel-group: prep]
**工具**: `crack_egg` [parallel-group: prep]
**工具**: `heat_pan` [depends-on: prep]
```
- `[parallel-group: xxx]`：将步骤归入并行组，同组步骤无互相依赖，可并行执行
- `[depends-on: xxx]`：显式依赖某个并行组（取该组最后一个步骤作为依赖点）

**Human-in-the-Loop 配置**（HITL 模式专用）：
```yaml
human_in_the_loop:
  - step: 4
    prompt: "确认油温合适，准备倒入蛋液进行滑炒？"
  - tool: season
    prompt: "确认要加入调味料吗？"
```
- 支持按 `step`（步骤编号）或 `tool`（工具名）触发人工确认
- `prompt` 中的 `{参数名}` 会被实际参数值替换

### Scripts（执行钩子）

放在 `scripts/` 下的 Python 脚本，通过 frontmatter 声明执行时机：

```yaml
scripts:
  pre: scripts/pre_check.py      # SOP 执行前运行
  post: scripts/post_cleanup.py  # SOP 执行后运行
```

脚本通过全局 `context` 对象访问 Skill 上下文：

```python
# scripts/pre_check.py
print(f"正在检查: {context.skill_name}")
meat = context.get("meat_type", "鸡腿肉")
context.output = "检查通过"
```

- `context.skill_name`：当前 Skill 名称
- `context.variables`：执行变量字典
- `context.get(key, default)`：安全读取变量
- `context.output`：脚本输出结果（会记录到日志）

### Reference（参考资料）

放在 `reference/` 下的 Markdown 文件，用于补充 SOP 中未详述的知识：

- **Demo 模式**：执行前提示已加载的参考资料数量
- **Agent 模式**：自动将所有参考文档拼接到 system prompt 中，给 LLM 更多上下文

### Templates（输出模板）

放在 `templates/` 下的 Markdown 文件，执行完成后渲染为结构化输出：

```yaml
templates:
  report: templates/dish_report.md
```

模板语法与 SOP 变量一致（`{{var_name}}`），渲染时会自动注入 `dish_name` 等变量。

### 子流程（Skill 复用）

通用步骤可以抽成独立的子 Skill，在其他 Skill 中引用：

```markdown
### 步骤 2: 腌制鸡肉
**子流程**: `marinate_meat`

将鸡丁放入碗中腌制 10 分钟入味。
```

执行时会自动加载 `skills/marinate_meat/SKILL.md` 的步骤并内联到当前位置。支持循环引用检测。

---

## Web UI 说明

前端基于 **Vite + TypeScript + Cytoscape.js**，提供 Skill 的可视化浏览：

| 区域 | 功能 |
|---|---|
| 左侧边栏 | Skill 列表，显示名称、描述、步骤数与工具数 |
| Markdown 面板 | 渲染选中 Skill 的完整 SOP 内容（食材、步骤、成功标准） |
| 流程图面板 | 用有向图展示步骤执行顺序，节点按工具类型着色 |

**节点颜色说明**：
- 🟥 切配 (`cut_ingredient`)
- 🟧 打蛋 (`crack_egg`)
- 🟨 热锅 (`heat_pan`)
- 🟩 炒制 (`stir_fry`)
- 🟦 调味 (`season`)
- 🟪 装盘 (`plate`)
- 🟫 子流程 (`marinate_meat` 等)

**构建流程**：
```bash
# 手动生成数据
python scripts/build_skills_json.py

# 或在前端目录下自动构建并启动
cd frontend
npm run dev    # 会自动执行 build:skills
```

---

## MCP 工具列表

| 工具名 | 功能 | 关键参数 |
|---|---|---|
| `cut_ingredient` | 切割食材 | `ingredient`, `method` |
| `crack_egg` | 打蛋 | `count`, `mix` |
| `heat_pan` | 热锅加油 | `temperature`, `duration` |
| `stir_fry` | 翻炒 | `ingredient`, `duration`, `technique` |
| `season` | 调味 | `salt`, `sugar`, `soy_sauce`, `other` |
| `plate` | 装盘 | `garnish` |

> 当前为 MOCK 实现，返回描述文本。实际场景中可替换为真实 API（如智能家居控制）。

---

## 日志说明

项目配置了**双通道日志**，同时输出到终端和本地文件：

| 日志来源 | 终端输出 | 文件位置 | 说明 |
|---|---|---|---|
| agent 侧 | ✅ stdout | `logs/YYYY-MM-DD.log` | 执行流程、步骤、结果 |
| MCP 服务端 | ✅ stderr | `logs/mcp_server_YYYY-MM-DD.log` | 工具调用参数、返回值 |

日志格式统一：
```
2026-06-04 16:53:35 | INFO     | kitchen_agent | 🍳 Demo 模式: 按 SOP 顺序执行
2026-06-04 16:53:36 | INFO     | mcp_server    | [TOOL CALL] cut_ingredient | args={...}
```

## 执行观测与审计

每次执行会自动生成结构化记录，保存到 `runs/<run_id>.json`：

```bash
# 列出最近 20 次执行
python backend/main.py --list-runs

# 回放某次执行（不调用真实工具，仅查看记录）
python backend/main.py --replay 59a3423e5165
```

记录内容包括：
- 执行元数据：run_id、skill_name、mode、variables、起止时间、整体状态
- 扩展字段：resumed_from（恢复来源）、rollback_to_step（回滚目标）、execution_plan（执行计划）
- 每一步详情：工具名、参数、执行结果/错误、耗时、并行组 ID、检查点 ID、人工审批记录

### 检查点与恢复

Resumable 模式会在每步执行前后自动保存检查点到 `runs/checkpoints/<run_id>_<cp_id>.json`：

```bash
# 带检查点的顺序执行
python backend/main.py --resumable --skill tomato_egg

# 执行中断后，从最新检查点恢复
python backend/main.py --resume <run_id>

# 回滚到某一步重新执行（创建新 run，保留原记录）
python backend/main.py --rollback <run_id> --to-step 3
```

检查点包含：当前步骤索引、步骤状态（before_step/after_step）、变量快照、已完成步骤结果。

---

## 扩展：新增一道菜

1. 在 `skills/` 下新建目录，如 `skills/mapo_tofu/`
2. 在目录中创建 `SKILL.md`，参考现有格式编写 SOP
3. 按需添加 `scripts/`、`reference/`、`templates/` 子目录
4. 确保引用的工具名在 `backend/mcp_server.py` 中存在
5. 运行测试：`python backend/main.py --demo --skill mapo_tofu`
6. 刷新前端页面即可看到新 Skill 的流程图

**核心原则**：Skill 只定义"做什么"和"参数是什么"，不定义工具怎么实现。工具实现由 MCP Server 负责。

---

## 技术栈

| 领域 | 技术 |
|---|---|
| 后端 | Python, LangChain, MCP (Model Context Protocol), PyYAML |
| 前端 | Vite, TypeScript, Cytoscape.js, Marked |
| 配置 | python-dotenv |

---

## License

MIT
