# 宫保鸡丁收工后清理

print("🧹 收工清理检查清单")

tasks = [
    "滑过油的锅必须趁热用热水清洗（油污冷却后难洗）",
    "检查灶台周围是否有溅出的油渍",
    "剩余碗汁倒掉，碗泡水中",
    "炸花生米密封保存，防止回潮",
]

for t in tasks:
    print(f"  - {t}")

context.output = "清理提醒已输出"
return_value = "cleanup_reminded"
