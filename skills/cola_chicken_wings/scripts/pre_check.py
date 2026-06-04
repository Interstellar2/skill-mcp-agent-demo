# 可乐鸡翅开炒前检查

print("=" * 40)
print("🥤 可乐鸡翅 - 开炒前检查")
print("=" * 40)

checklist = [
    ("鸡翅", "是否解冻完全？（表面无冰晶）"),
    ("可乐", "是否足量？（1 罐约 330ml）"),
    ("老抽", "是否有？（上色用，不可替代）"),
    ("白芝麻", "是否提前准备好？（最后点缀用）"),
]

for item, desc in checklist:
    print(f"  [ ] {item}: {desc}")

print("=" * 40)
print("⚠️  提醒：可乐鸡翅容易粘锅，煎鸡翅时不要用太大火")
print("=" * 40)

context.output = "可乐鸡翅检查完成"
return_value = "pre_check_passed"
