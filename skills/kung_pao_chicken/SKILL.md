---
name: kung_pao_chicken
description: 当用户要做宫保鸡丁、需要处理鸡肉和调配糊辣荔枝味碗汁时使用。
scripts:
  pre: scripts/pre_check.py
  post: scripts/post_cleanup.py
templates:
  report: templates/dish_report.md
tools:
  - cut_ingredient
  - heat_pan
  - stir_fry
  - season
  - plate
---

# 宫保鸡丁 SOP

## 食材准备
- 鸡腿肉 300g
- 大葱 2 根
- 干辣椒 10 个
- 花椒 1 小撮
- 油炸花生米 50g
- 食用油 适量

## 调料（碗汁）
- 白糖 2 大勺
- 陈醋 1 勺
- 生抽（酱油） 1 勺
- 料酒 1 勺
- 盐 少许
- 水淀粉 少许

## 操作步骤

### 步骤 1: 处理鸡肉
**工具**: `cut_ingredient`
**参数**:
- ingredient: "鸡腿肉"
- method: "去骨切丁"

将鸡腿肉去骨后切成约 1.5cm 见方的丁状，备用。

### 步骤 2: 腌制鸡肉
**子流程**: `marinate_meat`

将鸡丁放入碗中，加入盐、酱油、料酒和淀粉抓匀，腌制 10 分钟入味。

### 步骤 3: 处理配料
**工具**: `cut_ingredient`
**参数**:
- ingredient: "大葱"
- method: "切段"

大葱洗净切成约 2cm 长的段。

**工具**: `cut_ingredient`
**参数**:
- ingredient: "干辣椒"
- method: "切段"

干辣椒剪成段，去籽备用。

### 步骤 4: 热锅
**工具**: `heat_pan`
**参数**:
- temperature: "中大火"
- duration: 30

锅烧热后倒入足量食用油，油温烧至五六成热。

### 步骤 5: 滑炒鸡丁
**工具**: `stir_fry`
**参数**:
- ingredient: "鸡丁"
- duration: 60
- technique: "滑炒至变色"

下入腌好的鸡丁，快速滑炒至表面变色、断生后盛出备用。

### 步骤 6: 爆香辣椒花椒
**工具**: `stir_fry`
**参数**:
- ingredient: "干辣椒和花椒"
- duration: 15
- technique: "小火煸炒"

锅中留底油，小火下干辣椒段和花椒粒，慢慢煸炒出香味。

### 步骤 7: 合炒
**工具**: `stir_fry`
**参数**:
- ingredient: "鸡丁和大葱段"
- duration: 45
- technique: "大火翻炒"

倒入炒好的鸡丁和大葱段，大火快速翻炒均匀。

### 步骤 8: 淋入碗汁
**工具**: `season`
**参数**:
- salt: "少许"
- sugar: "2大勺"
- soy_sauce: "1勺"
- other: "陈醋1勺，料酒1勺，水淀粉少许"

将提前调好的碗汁沿锅边淋入，快速翻炒使芡汁均匀包裹住鸡丁。

### 步骤 9: 装盘
**工具**: `plate`
**参数**:
- garnish: "花生米"

最后倒入炸好的花生米，翻匀后立即出锅装盘。花生米保持酥脆口感。

## 坑点清单

- 鸡肉腌制时淀粉不要过多，否则滑炒时容易粘锅成团。
- 干辣椒和花椒必须小火煸炒，大火会迅速焦黑发苦。
- 碗汁要提前调好，入锅后需大火快炒，否则芡汁容易结块。
- 花生米最后放，久炒会回软，失去酥脆口感。

## 成功标准
- 鸡丁嫩滑不柴，大小均匀
- 味道呈现"糊辣荔枝味"：辣而不燥，酸中带甜
- 花生米酥脆，不能回软
- 芡汁明亮，均匀包裹食材
