# Kitchen SOP Demo - Skill + MCP + LangChain 演示项目

一个展示**结构化 Skill 管理**、**MCP 工具协议**、**LangChain Agent**、**多种执行编排模式**与**交互式 Web 控制面板**如何协同工作的演示项目。

用三道中餐菜谱（番茄炒蛋、宫保鸡丁、可乐鸡翅）作为示例，让 LLM 或直接按 SOP 流程调用"厨房工具"完成做菜，支持**计划-执行分离**、**人在回路**、**并行执行**与**断点续作/回滚**，并通过完整的 Web UI 实时控制执行、查看流程图高亮与执行日志。

---

## 项目架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Frontend (Browser)                          │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ Skill List  │  │ Execution    │  │ Cytoscape    │  │ Run       │ │
│  │ (Sidebar)   │  │ Control Bar  │  │ Flow Graph   │  │ History   │ │
│  └─────────────┘  └──────────────┘  └──────────────┘  └───────────┘ │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────────────┐│
│  │ Markdown     │  │ Real-time    │  │ HITL Modal / Agent Thinking ││
│  │ SOP Panel    │  │ Log Panel    │  │                             ││
│  └──────────────┘  └──────────────┘  └─────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
                              │ REST / WebSocket
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend (Uvicorn)                        │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────────────┐│
│  │ REST Router │  │ WebSocket    │  │ Orchestrator                 ││
│  │ /api/*      │  │ /ws/run/:id  │  │ (asyncio.Task per run)       ││
│  └─────────────┘  └──────────────┘  └──────────────────────────────┘│
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────────────┐│
│  │ HITL Bridge │  │ MCP Pool     │  │ RunTracker + WS Broadcast    ││
│  │ (asyncio.   │  │ (singleton   │  │ (executors integrate tracker ││
│  │  Future)    │  │  per app)    │  │  and broadcast events)       ││
│  └─────────────┘  └──────────────┘  └──────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Existing Backend Modules                         │
│  SkillsManager │ RunTracker │ Executors │ MCP Client │ Checkpoints  │
└─────────────────────────────────────────────────────────────────────┘
```

| 层级 | 职责 | 类比 |
|---|---|---|
| **Skill** | 定义"做什么"（SOP 流程、工具映射、参数） | 菜谱 |
| **Skill Manager / Parser** | 加载、解析、管理多个 Skill | 菜谱架 |
| **Executors** | 决定"怎么做"（顺序/LLM/并行/人在回路等） | 厨师大脑 |
| **MCP Server** | 实际"动手做"（工具实现） | 厨房设备 |
| **FastAPI Backend** | 统一 API 网关与执行管理 | 餐厅后厨调度台 |
| **Web UI** | 交互式控制面板：启动执行、实时高亮、HITL、日志 | 智能料理机屏幕 |

---

## 环境准备

### 1. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

依赖包括：`langchain`、`mcp`、`python-dotenv`、`pyyaml`、`fastapi`、`uvicorn` 等。

### 2. 安装前端依赖

```bash
cd frontend
npm install
```

### 3. 配置环境变量（可选，仅 Agent / Plan-then-Execute 模式需要）

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

### 启动后端 API 服务器

```bash
cd backend
python api_server.py
```

后端启动在 `http://localhost:8000`，提供 REST API 与 WebSocket：
- `GET /api/health` — 健康检查
- `GET /api/skills` — 列出所有 Skills
- `POST /api/runs` — 启动新执行
- `WS /ws/run/{run_id}` — 实时执行事件流

### 启动前端开发服务器

```bash
cd frontend
npm run dev
```

打开 http://localhost:5173/，左侧选择 Skill，使用顶部控制栏选择执行模式并点击 **Run**，即可在浏览器中实时观察步骤高亮、日志输出和 HITL 弹窗。

> `npm run dev` 会自动调用 `scripts/build_skills_json.py` 生成最新数据，Vite proxy 会将 `/api` 和 `/ws` 转发到后端的 8000 端口。

### CLI 模式（向后兼容）

所有原有 CLI 命令保持不变：

```bash
# Demo 模式（无需 API Key）
python backend/main.py --demo --skill tomato_egg

# Agent 模式（需要 LLM）
python backend/main.py --agent --skill tomato_egg

# Plan-then-Execute
python backend/main.py --plan-then-execute --skill tomato_egg

# HITL 模式
python backend/main.py --hitl --skill tomato_egg

# 并行执行
python backend/main.py --parallel --skill tomato_egg

# 断电续作 / 回滚
python backend/main.py --resumable --skill tomato_egg
python backend/main.py --resume <run_id>
python backend/main.py --rollback <run_id> --to-step 3

# 查看历史
python backend/main.py --list-runs
python backend/main.py --replay <run_id>
```

> 如果没有配置 `OPENAI_API_KEY`，Agent / Plan-then-Execute 会自动回退到 Demo 模式。

---

## Web UI 功能说明

前端基于 **Vue 3 + Pinia + Vite + TypeScript + Cytoscape.js**，提供完整的交互式执行控制面板：

| 区域 | 功能 |
|---|---|
| **左侧边栏** | Skill 列表，显示名称、描述、步骤数 |
| **执行控制栏** | 模式选择（Demo/Agent/Parallel/HITL 等）、变量表单、Run 按钮、WS 连接状态 |
| **Markdown 面板** | 渲染选中 Skill 的完整 SOP 内容 |
| **流程图面板** | Cytoscape 有向图展示步骤执行顺序，支持顺序/DAG/网格/环形布局切换 |
| **实时日志** | 结构化的步骤执行日志（开始/完成/错误） |
| **Agent Thinking** | 可折叠面板，展示 Agent 模式的工具选择与推理过程 |
| **HITL 弹窗** | 人在回路模式下弹出确认对话框，支持 Approve / Reject |
| **右侧历史** | 最近执行记录列表，点击查看详情 |

**流程图实时高亮**：
- 🔵 蓝色脉冲 — 步骤执行中 (`node-running`)
- 🟢 绿色 — 步骤成功 (`node-success`)
- 🔴 红色 — 步骤失败 (`node-error`)
- 🟣 紫色 — Parallel 模式当前批次 (`batch-active`)

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
│   ├── api_server.py                # FastAPI Uvicorn 入口
│   ├── main.py                      # CLI 命令行入口
│   ├── cli.py                       # 参数解析器（argparse）
│   ├── commands.py                  # 查询类命令（--list-runs / --replay）
│   ├── router.py                    # CLI 执行路由（模式解析 + executor 分发）
│   ├── mcp_server.py                # MCP 厨房工具服务器（独立进程）
│   ├── requirements.txt             # Python 依赖（含 fastapi / uvicorn）
│   └── kitchen_sop/                 # 核心包
│       ├── __init__.py
│       ├── config.py                # 环境变量加载、项目根目录常量
│       ├── logging_utils.py         # 统一日志配置
│       ├── skill/                   # Skill 解析与加载领域
│       │   ├── __init__.py
│       │   ├── manager.py           # Skill 扫描与解析（目录化结构）
│       │   ├── parser.py            # SOP Markdown 提取工具调用步骤（支持子流程内联）
│       │   ├── template.py          # 变量模板渲染（{{var}} 替换）
│       │   ├── script.py            # Skill 脚本执行引擎（pre/post hooks）
│       │   ├── reference.py         # 参考资料加载与格式化
│       │   └── validator.py         # SKILL 校验：工具存在性 + 参数 Schema 匹配
│       ├── mcp_client.py            # MCP 客户端连接管理（CLI 兼容）
│       ├── mcp_pool.py              # MCP 单例连接池（Web 并发共享）
│       ├── hitl_bridge.py           # HITL 异步信号桥（Web 模式）
│       ├── tracker/                 # 执行观测与审计
│       │   ├── __init__.py
│       │   ├── models.py            # RunRecord / StepRecord / ExecutionPlan / Checkpoint 数据模型
│       │   ├── checkpoint.py        # 检查点管理器（CheckpointManager）
│       │   └── core.py              # RunTracker 上下文管理器与持久化
│       ├── executors/               # 执行器（共享基类 + 6 种模式）
│       │   ├── __init__.py
│       │   ├── base.py              # SkillExecutorContext + execute_step 通用封装
│       │   ├── demo.py              # Demo 模式：按 SOP 顺序执行
│       │   ├── agent.py             # Agent 模式：LangChain + LLM 自主决策
│       │   ├── plan_then_execute.py # Plan-then-Execute：计划-执行分离
│       │   ├── hitl.py              # Human-in-the-Loop：人在回路
│       │   ├── parallel.py          # Parallel：DAG 拓扑并行执行
│       │   ├── resumable.py         # Resumable：检查点 + 自动断电续作
│       │   ├── resume.py            # Resume：从检查点恢复执行
│       │   └── rollback.py          # Rollback：回滚到指定步骤重试
│       └── api/                     # FastAPI Web 层
│           ├── __init__.py
│           ├── main.py              # FastAPI App（lifespan、CORS、router 挂载）
│           ├── routes.py            # REST API 路由实现
│           ├── ws.py                # WebSocket 连接管理与广播
│           ├── schemas.py           # Pydantic 请求/响应模型
│           └── orchestrator.py      # ActiveRun 管理与 start_run()
│
├── frontend/                        # Vue 3 + Pinia + Vite 前端
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts               # 含 dev proxy（/api → localhost:8000）
│   ├── tsconfig.json
│   ├── src/
│   │   ├── main.ts                  # Vue 3 入口（createApp + Pinia）
│   │   ├── App.vue                  # 根布局组件
│   │   ├── types.ts                 # 类型定义
│   │   ├── stores/                  # Pinia 状态管理
│   │   │   ├── app.ts               # Skill 选择与详情状态
│   │   │   └── run.ts               # 执行状态、日志、HITL、Agent 推理
│   │   ├── composables/             # 可复用逻辑
│   │   │   ├── useApi.ts            # REST API 封装
│   │   │   ├── useWebSocket.ts      # WebSocket 连接管理（自动重连）
│   │   │   ├── useCytoscape.ts      # Cytoscape 实例生命周期管理
│   │   │   └── useExecution.ts      # 执行控制逻辑（启动、HITL 响应）
│   │   ├── components/              # Vue SFC 组件
│   │   │   ├── SkillList.vue        # 左侧 Skill 列表
│   │   │   ├── SkillDetail.vue      # Markdown SOP 展示
│   │   │   ├── ExecutionPanel.vue   # 执行控制栏（模式、变量、Run）
│   │   │   ├── VariableForm.vue     # 动态变量输入表单
│   │   │   ├── GraphViewer.vue      # Cytoscape 流程图（布局切换 + 实时高亮）
│   │   │   ├── LogViewer.vue        # 实时执行日志
│   │   │   ├── HitlModal.vue        # HITL 确认弹窗
│   │   │   ├── RunHistory.vue       # 执行历史列表
│   │   │   ├── AgentThinking.vue    # Agent 推理过程面板（可折叠）
│   │   │   └── RunReplay.vue        # 历史回放控制
│   │   └── graph/                   # 图渲染工具函数
│   │       ├── render.ts            # Cytoscape 初始化与事件绑定
│   │       ├── styles.ts            # 节点/边样式配置（含执行状态样式）
│   │       └── dag-layout.ts        # DAG 边构建逻辑（Parallel 模式）
│   └── public/
│       └── skills_data.json         # 构建产物：Skill 数据（自动生成）
│
├── scripts/
│   └── build_skills_json.py         # 构建脚本：skills/ → frontend/public/skills_data.json
│
├── skills/                          # Skill 目录（每个 Skill 一个子目录）
│   ├── tomato_egg/                  # 番茄炒蛋（带变量 + scripts + reference + parallel-group）
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

## Backend API 设计

### REST Endpoints

| Method | Path | 描述 |
|--------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/skills` | 列出所有 Skills |
| GET | `/api/skills/{skill_name}` | 获取单个 Skill 详情 |
| POST | `/api/runs` | 启动新执行 |
| GET | `/api/runs` | 列出最近执行记录 |
| GET | `/api/runs/{run_id}` | 获取单次执行详情 |
| POST | `/api/runs/{run_id}/resume` | 从检查点恢复 |
| POST | `/api/runs/{run_id}/rollback` | 回滚到指定步骤 |
| POST | `/api/runs/{run_id}/approve` | HITL 人工确认 |
| GET | `/api/runs/{run_id}/checkpoints` | 获取检查点列表 |

### WebSocket 消息类型

**Server → Client**：
- `init` — 连接初始化
- `step_start` / `step_finish` / `step_error` — 步骤状态变更
- `hitl_request` — 暂停等待人工确认
- `plan_generated` — 计划已生成
- `batch_start` / `batch_finish` — Parallel 批次事件
- `agent_thought` — Agent 推理过程
- `checkpoint_saved` — 检查点已保存
- `run_complete` — 执行完成

**Client → Server**：
- `hitl_approval` — 发送 HITL 审批决定
- `ping` — 心跳

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

---

## 执行观测与审计

每次执行会自动生成结构化记录，保存到 `runs/<run_id>.json`：

```bash
# 通过 API 查看
python -c "import requests; print(requests.get('http://localhost:8000/api/runs').json())"

# 或通过 CLI
python backend/main.py --list-runs
python backend/main.py --replay 59a3423e5165
```

记录内容包括：
- 执行元数据：run_id、skill_name、mode、variables、起止时间、整体状态
- 扩展字段：resumed_from（恢复来源）、rollback_to_step（回滚目标）、execution_plan（执行计划）
- 每一步详情：工具名、参数、执行结果/错误、耗时、并行组 ID、检查点 ID、人工审批记录

### 检查点与恢复

Resumable 模式会在每步执行前后自动保存检查点到 `runs/checkpoints/<run_id>_<cp_id>.json`：

```bash
# Web UI 中点击 Run 选择 Resumable 模式即可
# 或通过 CLI
python backend/main.py --resumable --skill tomato_egg
python backend/main.py --resume <run_id>
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
6. 刷新前端页面即可看到新 Skill 的流程图并执行

**核心原则**：Skill 只定义"做什么"和"参数是什么"，不定义工具怎么实现。工具实现由 MCP Server 负责。

---

## 技术栈

| 领域 | 技术 |
|---|---|
| 后端 | Python, LangChain, MCP (Model Context Protocol), FastAPI, Uvicorn, PyYAML |
| 前端 | Vue 3, Pinia, Vite, TypeScript, Cytoscape.js, Marked |
| 配置 | python-dotenv |

---

## License

MIT
