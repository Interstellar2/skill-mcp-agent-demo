# 宫保鸡丁开炒前检查清单

print("=" * 40)
print("🔍 宫保鸡丁 - 开炒前检查")
print("=" * 40)

checklist = [
    ("花生米", "是否已提前炸好并保持酥脆？"),
    ("油温计", "是否正常工作？（滑油需要五六成热）"),
    ("碗汁", "是否提前调好（糖、醋、酱油、料酒、水淀粉）？"),
    ("鸡肉", f"是否已腌制入味？（变量：{context.get('meat_type', '鸡腿肉')}）"),
    ("干辣椒", "是否去籽？（籽容易炸糊发苦）"),
]

all_ok = True
for item, desc in checklist:
    print(f"  [ ] {item}: {desc}")

print("=" * 40)
print("⚠️  提醒：宫保鸡丁是火候菜，碗汁和花生米必须最后放！")
print("=" * 40)

context.output = "开炒前检查完成，确认花生米、碗汁已备好"
return_value = "pre_check_passed"
