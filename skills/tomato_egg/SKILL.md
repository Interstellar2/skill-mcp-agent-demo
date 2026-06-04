---
name: tomato_egg
description: 番茄炒鸡蛋标准操作流程（SOP），指导用户完成一道经典家常菜的制作。
scripts:
  pre: scripts/pre_check.py
templates:
  report: templates/dish_report.md
variables:
  egg_count:
    type: int
    default: 3
    description: 鸡蛋数量
tools:
  - cut_ingredient
  - crack_egg
  - heat_pan
  - stir_fry
  - season
  - plate
human_in_the_loop:
  - step: 4
    prompt: "确认油温合适，准备倒入蛋液进行滑炒？"
  - step: 7
    prompt: "确认调味已完成，准备装盘？"
---

# 番茄炒鸡蛋 SOP

## 食材准备
- 番茄 2 个
- 鸡蛋 {{egg_count}} 个
- 食用油 适量
- 盐 1 小勺
- 糖 1/2 小勺
- 葱花 少许（可选）

## 操作步骤

### 步骤 1: 处理番茄
**工具**: `cut_ingredient` [parallel-group: prep]
**参数**:
- ingredient: "番茄"
- method: "切块"

将番茄洗净后，切成大小均匀的块状备用。

### 步骤 2: 打蛋液
**工具**: `crack_egg` [parallel-group: prep]
**参数**:
- count: {{egg_count}}
- mix: true

将鸡蛋打入碗中，用筷子充分搅打均匀，直到蛋液表面出现细密泡沫。

### 步骤 3: 热锅
**工具**: `heat_pan` [depends-on: prep]
**参数**:
- temperature: "中大火"
- duration: 30

将锅置于灶上，开中大火预热约 30 秒，倒入适量食用油，晃动锅身使油均匀覆盖锅底。

### 步骤 4: 炒蛋
**工具**: `stir_fry`
**参数**:
- ingredient: "蛋液"
- duration: 30
- technique: "滑炒"

油热后倒入蛋液，用铲子快速滑炒，待蛋液凝固成块但还未完全熟透时，盛出备用。

### 步骤 5: 炒番茄
**工具**: `stir_fry`
**参数**:
- ingredient: "番茄块"
- duration: 60
- technique: "中火煸炒"

锅中加少许油，放入番茄块，中火煸炒至番茄出汁、变软。

### 步骤 6: 合炒调味
**工具**: `stir_fry`
**参数**:
- ingredient: "鸡蛋和番茄"
- duration: 30
- technique: "翻炒均匀"

将炒好的鸡蛋倒回锅中，与番茄一起翻炒均匀。

**工具**: `season`
**参数**:
- salt: "1小勺"
- sugar: "1/2小勺"

加入盐和糖调味，继续翻炒使味道均匀融合。

### 步骤 7: 装盘
**工具**: `plate`
**参数**:
- garnish: "葱花"

将炒好的番茄鸡蛋盛入盘中，撒上少许葱花点缀（可选）。

## 成功标准
- 鸡蛋嫩滑不焦糊
- 番茄出汁但仍有形状
- 味道咸鲜微甜，酸甜适口
- 色泽红亮诱人
