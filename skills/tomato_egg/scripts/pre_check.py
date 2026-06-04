# 番茄炒蛋开炒前检查

print("=" * 40)
print("🍅 番茄炒蛋 - 开炒前检查")
print("=" * 40)

checklist = [
    ("鸡蛋", f"是否有 {context.get('egg_count', 3)} 个新鲜鸡蛋？（摇晃无声音）"),
    ("番茄", "是否成熟多汁？（轻捏有弹性）"),
    ("锅具", "是否干净无水分？（炒蛋不粘锅）"),
    ("葱花", "是否提前切好备用？"),
]

for item, desc in checklist:
    print(f"  [ ] {item}: {desc}")

print("=" * 40)
print("💡 小贴士：番茄顶部划十字，开水烫 10 秒更易去皮")
print("=" * 40)

context.output = "番茄炒蛋检查完成"
return_value = "pre_check_passed"
