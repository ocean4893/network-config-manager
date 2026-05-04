# utils.py
import re
import tkinter as tk
from tkinter import ttk
#https://github.com/ocean4893/network-config-manager

def col_letter_to_index(letter: str) -> int:
    """将 Excel 列字母 (A, B, ..., AA, ...) 转换为 0‑based 索引"""
    letter = letter.upper()
    index = 0
    for char in letter:
        index = index * 26 + (ord(char) - ord('A') + 1)
    return index - 1


def template_replace(match, row_data: dict) -> str:
    """
    模板替换函数：
    {field} 直接替换为字段值
    {field+10} 支持加减乘除运算
    """
    field = match.group(1)
    op_num = match.group(2)  # 可能为 None，如 "+10"
    val = row_data.get(field, '')
    if op_num:
        try:
            num = float(val)
            op = op_num[0]
            operand = float(op_num[1:])
            if op == '+':
                result = num + operand
            elif op == '-':
                result = num - operand
            elif op == '*':
                result = num * operand
            elif op == '/':
                result = num / operand if operand != 0 else 0
            # 整型美化
            if result == int(result):
                result = int(result)
            return str(result)
        except (ValueError, TypeError):
            return str(val)
    return str(val)


def edit_tree_col_letter(event, tree):
    """
    双击 Treeview 的列字母列进行编辑。
    适用于配置生成/下发字段管理窗口。
    """
    region = tree.identify("region", event.x, event.y)
    if region != "cell":
        return
    column = tree.identify_column(event.x)
    if column != "#2":  # 列字母是第二列
        return
    item = tree.identify_row(event.y)
    if not item:
        return
    col_bbox = tree.bbox(item, column)
    if not col_bbox:
        return
    x, y, width, height = col_bbox
    current_val = tree.item(item, "values")[1]
    entry = ttk.Entry(tree, width=5)
    entry.place(x=x, y=y, width=width, height=height)
    entry.insert(0, current_val)
    entry.focus_set()

    def save(ev=None):
        new_val = entry.get().strip().upper()
        if re.match(r'^[A-Z]$', new_val):
            vals = list(tree.item(item, "values"))
            vals[1] = new_val
            tree.item(item, values=tuple(vals))
        entry.destroy()

    entry.bind("<Return>", save)
    entry.bind("<FocusOut>", save)