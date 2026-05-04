# tools/generator.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import re
import pyperclip
from datetime import datetime
from tools import utils   # 或 from . import utils，根据你的实际情况调整

#https://github.com/ocean4893/network-config-manager
class ConfigGenerator:
    def __init__(self, root, back_callback=None):
        self.root = root
        self.back_callback = back_callback

        # 生成器状态
        self.df = None
        self.file_name = ""
        self.fields = []          # 字段定义：[{name: str, col_letter: str}]
        self.start_row = 1
        self.template = ""
        self.current_data_row_index = 0
        self.generated_config = ""

        # UI 框架（延迟创建）
        self.frame = None
        self.built = False

    def show_page(self):
        """显示生成器界面"""
        if not self.built:
            self._build_page()
            self.built = True
        self.frame.pack(expand=True, fill="both")

    def hide_page(self):
        """隐藏生成器界面"""
        if self.frame:
            self.frame.pack_forget()

    def _build_page(self):
        self.frame = ttk.Frame(self.root)

        toolbar = ttk.Frame(self.frame)
        toolbar.pack(fill="x", padx=10, pady=5)

        self.btn_load = ttk.Button(toolbar, text="加载excel文件", command=self.load_excel)
        self.btn_load.pack(side="left", padx=5)

        self.btn_fields = ttk.Button(toolbar, text="执行字段列", command=self.manage_fields)
        self.btn_fields.pack(side="left", padx=5)

        self.btn_template = ttk.Button(toolbar, text="配置生成模板", command=self.edit_template)
        self.btn_template.pack(side="left", padx=5)

        self.btn_generate = ttk.Button(toolbar, text="开始生成", command=self.start_generate)
        self.btn_generate.pack(side="left", padx=5)

        self.lbl_file_status = ttk.Label(self.frame, text="未加载文件", foreground="gray")
        self.lbl_file_status.pack(anchor="w", padx=10, pady=2)

        paned = ttk.PanedWindow(self.frame, orient="horizontal")
        paned.pack(expand=True, fill="both", padx=10, pady=5)

        left_frame = ttk.LabelFrame(paned, text="当前配置模板")
        paned.add(left_frame, weight=1)
        self.txt_template_display = tk.Text(left_frame, wrap="none", state="disabled",
                                            font=("Consolas", 10))
        self.txt_template_display.pack(expand=True, fill="both")

        right_frame = ttk.LabelFrame(paned, text="生成的配置")
        paned.add(right_frame, weight=1)
        self.txt_output = tk.Text(right_frame, wrap="none", font=("Consolas", 10))
        self.txt_output.pack(expand=True, fill="both")

        bottom_frame = ttk.Frame(self.frame)
        bottom_frame.pack(fill="x", padx=10, pady=5)

        # 按钮区：复制、上一个、下一个、返回主菜单
        self.btn_copy = ttk.Button(bottom_frame, text="复制", command=self.copy_config)
        self.btn_copy.pack(side="left", padx=5)

        self.btn_prev = ttk.Button(bottom_frame, text="上一个", command=self.prev_generate)
        self.btn_prev.pack(side="left", padx=5)

        self.btn_next = ttk.Button(bottom_frame, text="下一个", command=self.next_generate)
        self.btn_next.pack(side="left", padx=5)

        self.btn_back = ttk.Button(bottom_frame, text="返回主菜单", command=self._back)
        self.btn_back.pack(side="right", padx=5)

    def _back(self):
        self.hide_page()
        if self.back_callback:
            self.back_callback()

    # ========== 核心方法 ==========
    def load_excel(self):
        file_path = filedialog.askopenfilename(
            title="选择 Excel 或 CSV 文件",
            filetypes=[("表格文件", "*.xlsx *.xls *.csv"), ("所有文件", "*.*")]
        )
        if not file_path:
            return
        try:
            if file_path.lower().endswith('.csv'):
                self.df = pd.read_csv(file_path, header=None)
            else:
                self.df = pd.read_excel(file_path, header=None, sheet_name=0)
            self.file_name = file_path.split('/')[-1].split('\\')[-1]
            self.lbl_file_status.config(text=f"已加载：{self.file_name}", foreground="green")
            messagebox.showinfo("成功", f"文件 {self.file_name} 加载成功，共 {len(self.df)} 行。")
        except Exception as e:
            messagebox.showerror("加载失败", f"无法读取文件：{str(e)}")

    def manage_fields(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("执行字段列")
        dialog.geometry("450x400")
        dialog.resizable(False, False)
        dialog.grab_set()

        frame_top = ttk.Frame(dialog)
        frame_top.pack(fill="both", expand=True, padx=10, pady=10)

        columns = ("字段名", "列字母")
        self.fields_tree = ttk.Treeview(frame_top, columns=columns, show="headings", height=6)
        self.fields_tree.heading("字段名", text="字段名")
        self.fields_tree.heading("列字母", text="列字母 (A-Z)")
        self.fields_tree.column("字段名", width=150)
        self.fields_tree.column("列字母", width=100)
        self.fields_tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(frame_top, orient="vertical", command=self.fields_tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.fields_tree.configure(yscrollcommand=scrollbar.set)

        for f in self.fields:
            self.fields_tree.insert("", "end", values=(f["name"], f["col_letter"]))

        self.fields_tree.bind("<Double-1>", lambda e, t=self.fields_tree: utils.edit_tree_col_letter(e, t))

        edit_frame = ttk.Frame(dialog)
        edit_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(edit_frame, text="字段名:").grid(row=0, column=0, padx=2, pady=2, sticky="w")
        self.entry_field_name = ttk.Entry(edit_frame, width=15)
        self.entry_field_name.grid(row=0, column=1, padx=2, pady=2)

        ttk.Label(edit_frame, text="列字母:").grid(row=0, column=2, padx=2, pady=2, sticky="w")
        self.entry_col_letter = ttk.Entry(edit_frame, width=8)
        self.entry_col_letter.grid(row=0, column=3, padx=2, pady=2)

        btn_add = ttk.Button(edit_frame, text="添加", command=self.add_field)
        btn_add.grid(row=0, column=4, padx=5)

        btn_del = ttk.Button(edit_frame, text="删除选中", command=self.delete_field)
        btn_del.grid(row=0, column=5, padx=5)

        row_frame = ttk.Frame(dialog)
        row_frame.pack(fill="x", padx=10, pady=10)
        ttk.Label(row_frame, text="配置生成时开始行号 (1-based):").pack(side="left")
        self.var_start_row = tk.IntVar(value=self.start_row)
        spin_start = ttk.Spinbox(row_frame, from_=1, to=9999, textvariable=self.var_start_row, width=8)
        spin_start.pack(side="left", padx=5)

        def on_ok():
            new_fields = []
            for child in self.fields_tree.get_children():
                values = self.fields_tree.item(child, "values")
                name = values[0].strip()
                col_letter = values[1].strip().upper()
                if name and col_letter:
                    if not re.match(r'^[A-Z]$', col_letter):
                        messagebox.showerror("格式错误", f"列字母 '{col_letter}' 无效，必须为单个字母 A-Z。")
                        return
                    new_fields.append({"name": name, "col_letter": col_letter})
            self.fields = new_fields
            self.start_row = self.var_start_row.get()
            messagebox.showinfo("已保存", "字段和开始行已更新。")
            dialog.destroy()

        btn_ok = ttk.Button(dialog, text="确定", command=on_ok)
        btn_ok.pack(pady=10)

    def add_field(self):
        name = self.entry_field_name.get().strip()
        col_letter = self.entry_col_letter.get().strip().upper()
        if not name or not col_letter:
            messagebox.showwarning("输入不完整", "字段名和列字母都不能为空。")
            return
        if not re.match(r'^[A-Z]$', col_letter):
            messagebox.showerror("格式错误", "列字母必须为单个大写字母 A-Z。")
            return
        for child in self.fields_tree.get_children():
            existing_name = self.fields_tree.item(child, "values")[0]
            if existing_name == name:
                messagebox.showwarning("重复", f"字段名 '{name}' 已存在。")
                return
        self.fields_tree.insert("", "end", values=(name, col_letter))
        self.entry_field_name.delete(0, "end")
        self.entry_col_letter.delete(0, "end")

    def delete_field(self):
        selected = self.fields_tree.selection()
        if not selected:
            messagebox.showinfo("提示", "请先选中要删除的字段。")
            return
        for item in selected:
            self.fields_tree.delete(item)

    def edit_template(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("配置生成模板")
        dialog.geometry("500x600")
        dialog.grab_set()

        ttk.Label(dialog, text="编辑模板（使用 {字段名} 引用字段）:").pack(anchor="w", padx=10, pady=5)

        txt = tk.Text(dialog, wrap="none", font=("Consolas", 10))
        txt.pack(side="top", expand=True, fill="both", padx=10, pady=(5, 0))

        if self.template:
            txt.insert("1.0", self.template)
        else:
            default_tmpl = ("system-view\n"
                            "vlan batch {vlan_number}\n"
                            "interface vlan {vlan_number}\n"
                            "ip address {ip_address}")
            txt.insert("1.0", default_tmpl)

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(side="bottom", fill="x", padx=10, pady=10)

        def on_ok():
            template_text = txt.get("1.0", "end-1c")
            variables = {m.group(1) for m in re.finditer(r'\{(\w+)(?:[+\-*/]\d+)?\}', template_text)}
            field_names = [f["name"] for f in self.fields]
            missing = [v for v in variables if v not in field_names]
            if missing:
                messagebox.showerror("变量不存在",
                                     f"以下变量在字段列中未定义：{', '.join(set(missing))}")
                return
            self.template = template_text
            self.txt_template_display.config(state="normal")
            self.txt_template_display.delete("1.0", "end")
            self.txt_template_display.insert("1.0", self.template)
            self.txt_template_display.config(state="disabled")
            messagebox.showinfo("已保存", "模板已更新。")
            dialog.destroy()

        btn_ok = ttk.Button(btn_frame, text="确定", command=on_ok)
        btn_ok.pack(side="left", padx=5)
        btn_cancel = ttk.Button(btn_frame, text="取消", command=dialog.destroy)
        btn_cancel.pack(side="right", padx=5)

    def start_generate(self):
        if self.df is None:
            messagebox.showerror("错误", "请先加载 Excel 文件。")
            return
        if not self.fields:
            messagebox.showerror("错误", "请先定义字段列。")
            return
        if not self.template:
            messagebox.showerror("错误", "请先编辑配置模板。")
            return
        start_idx = self.start_row - 1
        if start_idx >= len(self.df):
            messagebox.showerror("错误", f"开始行 {self.start_row} 超出文件总行数 {len(self.df)}。")
            return
        self.current_data_row_index = 0
        self.generate_by_index()

    def next_generate(self):
        if self.df is None or not self.fields or not self.template:
            messagebox.showwarning("提示", "请先完成初始生成。")
            return
        self.current_data_row_index += 1
        self.generate_by_index()

    def prev_generate(self):
        """新增：生成上一条配置"""
        if self.df is None or not self.fields or not self.template:
            messagebox.showwarning("提示", "请先完成初始生成。")
            return
        if self.current_data_row_index == 0:
            messagebox.showinfo("提示", "已经是第一条配置，没有上一条。")
            return
        self.current_data_row_index -= 1
        self.generate_by_index()

    def generate_by_index(self):
        start_idx = self.start_row - 1
        data_row = start_idx + self.current_data_row_index
        if data_row >= len(self.df):
            messagebox.showinfo("提示", "已到达数据末尾。")
            self.current_data_row_index -= 1
            return

        row_data = {}
        for f in self.fields:
            col_letter = f["col_letter"]
            col_idx = utils.col_letter_to_index(col_letter)
            try:
                val = self.df.iloc[data_row, col_idx]
            except IndexError:
                val = None
            if pd.isna(val):
                val = ""
            else:
                val = str(val)
            row_data[f["name"]] = val
        config = re.sub(r'\{(\w+)([+\-*/]\d+)?\}',
                        lambda m: utils.template_replace(m, row_data),
                        self.template)
        self.generated_config = config
        self.txt_output.delete("1.0", "end")
        self.txt_output.insert("1.0", config)
        self.lbl_file_status.config(text=f"已加载：{self.file_name} | 当前行：{data_row + 1}")

        try:
            with open("generate_runtime_logs.txt", "a", encoding="utf-8") as log:
                log.write(f"===== {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 行{data_row + 1} =====\n")
                log.write(config + "\n\n")
        except Exception as e:
            print("无法写入日志:", e)

    def copy_config(self):
        if not self.generated_config:
            messagebox.showinfo("提示", "没有可复制的配置。")
            return
        pyperclip.copy(self.generated_config)
        messagebox.showinfo("已复制", "生成的配置已复制到剪贴板。")