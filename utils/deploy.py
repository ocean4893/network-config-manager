# deploy.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import re
import threading
import time
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import paramiko
from tools import utils
#https://github.com/ocean4893/network-config-manager

class ConfigDeployer:#批量配置下发器
    def __init__(self, root, back_callback=None):
        self.root = root
        self.back_callback = back_callback

        # 下发状态
        self.deploy_df = None
        self.deploy_file_name = ""
        self.deploy_fields = [
            {"name": "host_ip", "col_letter": "B"},
            {"name": "user_name", "col_letter": "C"},
            {"name": "user_password", "col_letter": "D"}
        ]
        self.deploy_start_row = 1
        self.deploy_template = ""
        self.deploy_thread_count = tk.IntVar(value=5)
        self.deploy_save_enabled = tk.BooleanVar(value=False)
        self.deploy_save_command = "save force"
        self.deploy_save_detect = "Validating file. Please wait..."
        self.deploy_running = False

        # 日志文件
        self.deploy_log_file = "deploy_runtime.log"
        self.deploy_success_file = "deploy_success.txt"
        self.deploy_fail_file = "deploy_failure.txt"

        self.frame = None
        self.built = False

    def show_page(self):
        if not self.built:
            self._build_page()
            self.built = True
        self.frame.pack(expand=True, fill="both")

    def hide_page(self):
        if self.frame:
            self.frame.pack_forget()

    def _build_page(self):
        self.frame = ttk.Frame(self.root)

        toolbar = ttk.Frame(self.frame)
        toolbar.pack(fill="x", padx=10, pady=5)

        self.deploy_btn_load = ttk.Button(toolbar, text="加载excel文件", command=self.load_deploy_excel)
        self.deploy_btn_load.pack(side="left", padx=5)

        self.deploy_btn_fields = ttk.Button(toolbar, text="执行字段列", command=self.manage_deploy_fields)
        self.deploy_btn_fields.pack(side="left", padx=5)

        self.deploy_btn_template = ttk.Button(toolbar, text="配置生成模板", command=self.edit_deploy_template)
        self.deploy_btn_template.pack(side="left", padx=5)

        ttk.Label(toolbar, text="线程数量:").pack(side="left", padx=(15, 2))
        self.deploy_spin_thread = ttk.Spinbox(toolbar, from_=1, to=100, textvariable=self.deploy_thread_count, width=5)
        self.deploy_spin_thread.pack(side="left")

        self.deploy_chk_save = ttk.Checkbutton(toolbar, text="保存检测", variable=self.deploy_save_enabled,
                                               command=self.on_save_check_toggle)
        self.deploy_chk_save.pack(side="left", padx=15)

        self.deploy_btn_start = ttk.Button(toolbar, text="开始下发", command=self.start_deploy)
        self.deploy_btn_start.pack(side="left", padx=15)

        self.deploy_lbl_status = ttk.Label(self.frame, text="未加载文件", foreground="gray")
        self.deploy_lbl_status.pack(anchor="w", padx=10, pady=2)

        paned = ttk.PanedWindow(self.frame, orient="horizontal")
        paned.pack(expand=True, fill="both", padx=10, pady=5)

        left_frame = ttk.LabelFrame(paned, text="预计下发配置")
        paned.add(left_frame, weight=1)
        self.deploy_txt_template = tk.Text(left_frame, wrap="none", state="disabled",
                                           font=("Consolas", 10))
        self.deploy_txt_template.pack(expand=True, fill="both")

        mid_frame = ttk.LabelFrame(paned, text="准备下发设备")
        paned.add(mid_frame, weight=1)
        self.deploy_mid_listbox = tk.Listbox(mid_frame, font=("Consolas", 10))
        self.deploy_mid_listbox.pack(expand=True, fill="both")

        right_frame = ttk.LabelFrame(paned, text="正在下发设备")
        paned.add(right_frame, weight=1)
        self.deploy_right_listbox = tk.Listbox(right_frame, font=("Consolas", 10))
        self.deploy_right_listbox.pack(expand=True, fill="both")

        bottom_frame = ttk.Frame(self.frame)
        bottom_frame.pack(fill="x", padx=10, pady=5)

        self.deploy_btn_back = ttk.Button(bottom_frame, text="返回主菜单", command=self._back)
        self.deploy_btn_back.pack(side="right", padx=5)

    def _back(self):
        if self.deploy_running:
            if not messagebox.askyesno("确认退出", "下发任务正在执行，确定返回主菜单吗？"):
                return
        self.hide_page()
        if self.back_callback:
            self.back_callback()

    # ---- 下发辅助方法 ----
    def load_deploy_excel(self):
        file_path = filedialog.askopenfilename(
            title="选择 Excel 或 CSV 文件",
            filetypes=[("表格文件", "*.xlsx *.xls *.csv"), ("所有文件", "*.*")]
        )
        if not file_path:
            return
        try:
            if file_path.lower().endswith('.csv'):
                self.deploy_df = pd.read_csv(file_path, header=None)
            else:
                self.deploy_df = pd.read_excel(file_path, header=None, sheet_name=0)
            self.deploy_file_name = file_path.split('/')[-1].split('\\')[-1]
            self.deploy_lbl_status.config(text=f"已加载：{self.deploy_file_name}", foreground="green")
            self.refresh_mid_list()
            messagebox.showinfo("成功", f"文件 {self.deploy_file_name} 加载成功，共 {len(self.deploy_df)} 行。")
        except Exception as e:
            messagebox.showerror("加载失败", f"无法读取文件：{str(e)}")

    def refresh_mid_list(self):
        """根据当前字段读取所有IP并填充中间列表"""
        self.deploy_mid_listbox.delete(0, tk.END)
        if self.deploy_df is None:
            return
        host_ip_field = next((f for f in self.deploy_fields if f["name"] == "host_ip"), None)
        if not host_ip_field:
            return
        col_idx = utils.col_letter_to_index(host_ip_field["col_letter"])
        start_idx = self.deploy_start_row - 1
        for i in range(start_idx, len(self.deploy_df)):
            try:
                val = self.deploy_df.iloc[i, col_idx]
            except IndexError:
                break
            if pd.isna(val):
                continue
            ip = str(val).strip()
            if ip:
                self.deploy_mid_listbox.insert(tk.END, ip)

    def manage_deploy_fields(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("执行字段列 - 下发")
        dialog.geometry("450x400")
        dialog.resizable(False, False)
        dialog.grab_set()

        frame_top = ttk.Frame(dialog)
        frame_top.pack(fill="both", expand=True, padx=10, pady=10)

        columns = ("字段名", "列字母")
        self.deploy_fields_tree = ttk.Treeview(frame_top, columns=columns, show="headings", height=6)
        self.deploy_fields_tree.heading("字段名", text="字段名")
        self.deploy_fields_tree.heading("列字母", text="列字母 (A-Z)")
        self.deploy_fields_tree.column("字段名", width=150)
        self.deploy_fields_tree.column("列字母", width=100)
        self.deploy_fields_tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(frame_top, orient="vertical", command=self.deploy_fields_tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.deploy_fields_tree.configure(yscrollcommand=scrollbar.set)

        for f in self.deploy_fields:
            self.deploy_fields_tree.insert("", "end", values=(f["name"], f["col_letter"]))

        self.deploy_fields_tree.bind("<Double-1>",
                                     lambda e, t=self.deploy_fields_tree: utils.edit_tree_col_letter(e, t))

        edit_frame = ttk.Frame(dialog)
        edit_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(edit_frame, text="字段名:").grid(row=0, column=0, padx=2, pady=2, sticky="w")
        self.deploy_entry_name = ttk.Entry(edit_frame, width=15)
        self.deploy_entry_name.grid(row=0, column=1, padx=2, pady=2)

        ttk.Label(edit_frame, text="列字母:").grid(row=0, column=2, padx=2, pady=2, sticky="w")
        self.deploy_entry_col = ttk.Entry(edit_frame, width=8)
        self.deploy_entry_col.grid(row=0, column=3, padx=2, pady=2)

        btn_add = ttk.Button(edit_frame, text="添加", command=self.add_deploy_field)
        btn_add.grid(row=0, column=4, padx=5)

        btn_del = ttk.Button(edit_frame, text="删除选中", command=self.delete_deploy_field)
        btn_del.grid(row=0, column=5, padx=5)

        row_frame = ttk.Frame(dialog)
        row_frame.pack(fill="x", padx=10, pady=10)
        ttk.Label(row_frame, text="下发开始行号 (1-based):").pack(side="left")
        self.deploy_var_start_row = tk.IntVar(value=self.deploy_start_row)
        spin_start = ttk.Spinbox(row_frame, from_=1, to=9999, textvariable=self.deploy_var_start_row, width=8)
        spin_start.pack(side="left", padx=5)

        def on_ok():
            new_fields = []
            for child in self.deploy_fields_tree.get_children():
                values = self.deploy_fields_tree.item(child, "values")
                name = values[0].strip()
                col_letter = values[1].strip().upper()
                if name and col_letter:
                    if not re.match(r'^[A-Z]$', col_letter):
                        messagebox.showerror("格式错误", f"列字母 '{col_letter}' 无效，必须为单个字母 A-Z。")
                        return
                    new_fields.append({"name": name, "col_letter": col_letter})
            self.deploy_fields = new_fields
            self.deploy_start_row = self.deploy_var_start_row.get()
            messagebox.showinfo("已保存", "字段和开始行已更新。")
            dialog.destroy()
            self.refresh_mid_list()

        btn_ok = ttk.Button(dialog, text="确定", command=on_ok)
        btn_ok.pack(pady=10)

    def add_deploy_field(self):
        name = self.deploy_entry_name.get().strip()
        col_letter = self.deploy_entry_col.get().strip().upper()
        if not name or not col_letter:
            messagebox.showwarning("输入不完整", "字段名和列字母都不能为空。")
            return
        if not re.match(r'^[A-Z]$', col_letter):
            messagebox.showerror("格式错误", "列字母必须为单个大写字母 A-Z。")
            return
        for child in self.deploy_fields_tree.get_children():
            existing_name = self.deploy_fields_tree.item(child, "values")[0]
            if existing_name == name:
                messagebox.showwarning("重复", f"字段名 '{name}' 已存在。")
                return
        self.deploy_fields_tree.insert("", "end", values=(name, col_letter))
        self.deploy_entry_name.delete(0, "end")
        self.deploy_entry_col.delete(0, "end")

    def delete_deploy_field(self):
        selected = self.deploy_fields_tree.selection()
        if not selected:
            messagebox.showinfo("提示", "请先选中要删除的字段。")
            return
        for item in selected:
            self.deploy_fields_tree.delete(item)

    def edit_deploy_template(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("配置生成模板 - 下发")
        dialog.geometry("500x600")
        dialog.grab_set()

        ttk.Label(dialog, text="编辑模板（使用 {字段名} 引用字段）:").pack(anchor="w", padx=10, pady=5)

        txt = tk.Text(dialog, wrap="none", font=("Consolas", 10))
        txt.pack(side="top", expand=True, fill="both", padx=10, pady=(5, 0))

        if self.deploy_template:
            txt.insert("1.0", self.deploy_template)
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
            field_names = [f["name"] for f in self.deploy_fields]
            missing = [v for v in variables if v not in field_names]
            if missing:
                messagebox.showerror("变量不存在",
                                     f"以下变量在字段列中未定义：{', '.join(set(missing))}")
                return
            self.deploy_template = template_text
            self.update_deploy_preview()
            messagebox.showinfo("已保存", "模板已更新，左视图已切换为预计下发配置预览。")
            dialog.destroy()

        btn_ok = ttk.Button(btn_frame, text="确定", command=on_ok)
        btn_ok.pack(side="left", padx=5)
        btn_cancel = ttk.Button(btn_frame, text="取消", command=dialog.destroy)
        btn_cancel.pack(side="right", padx=5)

    def update_deploy_preview(self):
        if self.deploy_df is None or not self.deploy_fields or not self.deploy_template:
            preview = "无预览数据：请先加载Excel、定义字段并保存模板。"
        else:
            start_idx = self.deploy_start_row - 1
            if start_idx >= len(self.deploy_df):
                preview = "开始行超出数据范围，无法生成预览。"
            else:
                row_data = {}
                for f in self.deploy_fields:
                    col_idx = utils.col_letter_to_index(f["col_letter"])
                    try:
                        val = self.deploy_df.iloc[start_idx, col_idx]
                    except IndexError:
                        val = None
                    if pd.isna(val):
                        val = ""
                    else:
                        val = str(val)
                    row_data[f["name"]] = val
                preview = re.sub(r'\{(\w+)([+\-*/]\d+)?\}',
                                 lambda m: utils.template_replace(m, row_data),
                                 self.deploy_template)
        self.deploy_txt_template.config(state="normal")
        self.deploy_txt_template.delete("1.0", "end")
        self.deploy_txt_template.insert("1.0", preview)
        self.deploy_txt_template.config(state="disabled")

    def on_save_check_toggle(self):
        if self.deploy_save_enabled.get():
            dialog = tk.Toplevel(self.root)
            dialog.title("保存检测设置")
            dialog.geometry("400x200")
            dialog.grab_set()

            ttk.Label(dialog, text="保存命令:").pack(anchor="w", padx=10, pady=(10, 0))
            entry_cmd = ttk.Entry(dialog, width=40)
            entry_cmd.pack(padx=10, pady=2)
            entry_cmd.insert(0, self.deploy_save_command)

            ttk.Label(dialog, text="保存检测字符串:").pack(anchor="w", padx=10, pady=(10, 0))
            entry_detect = ttk.Entry(dialog, width=40)
            entry_detect.pack(padx=10, pady=2)
            entry_detect.insert(0, self.deploy_save_detect)

            def on_ok():
                self.deploy_save_command = entry_cmd.get().strip()
                self.deploy_save_detect = entry_detect.get().strip()
                if not self.deploy_save_command or not self.deploy_save_detect:
                    messagebox.showwarning("输入不完整", "保存命令和检测字符串不能为空。")
                    return
                dialog.destroy()

            def on_cancel():
                self.deploy_save_enabled.set(False)
                dialog.destroy()

            btn_ok = ttk.Button(dialog, text="确定", command=on_ok)
            btn_ok.pack(side="left", padx=20, pady=15)
            btn_cancel = ttk.Button(dialog, text="取消", command=on_cancel)
            btn_cancel.pack(side="right", padx=20, pady=15)

    # ---- 下发核心逻辑 ----
    def start_deploy(self):
        if self.deploy_running:
            messagebox.showwarning("提示", "下发任务已在进行中。")
            return
        if self.deploy_df is None:
            messagebox.showerror("错误", "请先加载 Excel 文件。")
            return
        if not self.deploy_fields:
            messagebox.showerror("错误", "请先定义字段列。")
            return
        if not self.deploy_template:
            messagebox.showerror("错误", "请先编辑配置模板。")
            return

        host_ip_f = next((f for f in self.deploy_fields if f["name"] == "host_ip"), None)
        user_f = next((f for f in self.deploy_fields if f["name"] == "user_name"), None)
        pass_f = next((f for f in self.deploy_fields if f["name"] == "user_password"), None)
        if not all([host_ip_f, user_f, pass_f]):
            messagebox.showerror("错误", "必须字段 host_ip、user_name、user_password 缺失。")
            return

        host_ip_col = utils.col_letter_to_index(host_ip_f["col_letter"])
        user_col = utils.col_letter_to_index(user_f["col_letter"])
        pass_col = utils.col_letter_to_index(pass_f["col_letter"])

        tasks = []
        start_idx = self.deploy_start_row - 1
        for i in range(start_idx, len(self.deploy_df)):
            try:
                host_ip = str(self.deploy_df.iloc[i, host_ip_col]).strip()
                username = str(self.deploy_df.iloc[i, user_col]).strip()
                password = str(self.deploy_df.iloc[i, pass_col]).strip()
            except IndexError:
                continue
            if pd.isna(self.deploy_df.iloc[i, host_ip_col]) or host_ip == "":
                continue
            row_data = {}
            for f in self.deploy_fields:
                c = utils.col_letter_to_index(f["col_letter"])
                try:
                    val = self.deploy_df.iloc[i, c]
                except IndexError:
                    val = None
                if pd.isna(val):
                    val = ""
                else:
                    val = str(val)
                row_data[f["name"]] = val
            config_str = re.sub(r'\{(\w+)([+\-*/]\d+)?\}',
                                lambda m: utils.template_replace(m, row_data),
                                self.deploy_template)
            commands = [line.rstrip('\r') for line in config_str.split('\n') if line.strip() != '']
            if not commands:
                continue
            if self.deploy_save_enabled.get():
                commands.append(self.deploy_save_command)
            tasks.append({
                "ip": host_ip,
                "username": username,
                "password": password,
                "commands": commands,
                "row": i + 1
            })

        if not tasks:
            messagebox.showinfo("提示", "没有可供下发的设备。")
            return

        thread_count = self.deploy_thread_count.get()
        if thread_count < 1:
            thread_count = 1

        self.deploy_mid_listbox.delete(0, tk.END)
        self.deploy_right_listbox.delete(0, tk.END)
        self.deploy_running = True
        self.deploy_btn_start.config(state="disabled")
        self.deploy_btn_load.config(state="disabled")
        self.deploy_btn_fields.config(state="disabled")
        self.deploy_btn_template.config(state="disabled")
        self.deploy_btn_back.config(state="disabled")

        # 启动后台线程
        threading.Thread(target=self.run_deploy_tasks, args=(tasks, thread_count), daemon=True).start()

    def run_deploy_tasks(self, tasks, max_workers):
        executor = ThreadPoolExecutor(max_workers=max_workers)
        futures = [executor.submit(self.deploy_single_device, task) for task in tasks]

        for future in as_completed(futures):
            pass

        executor.shutdown(wait=True)
        self.root.after(0, self.on_deploy_finished)

    def deploy_single_device(self, task):
        ip = task["ip"]
        username = task["username"]
        password = task["password"]
        commands = task["commands"]

        self.root.after(0, lambda: self.deploy_right_listbox.insert(tk.END, ip))

        log_entries = [f"===== {datetime.now()} 开始处理 {ip} ====="]
        success = False
        fail_reason = ""

        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname=ip, port=22, username=username, password=password,
                        timeout=10, look_for_keys=False, allow_agent=False)
            shell = ssh.invoke_shell()
            time.sleep(1)
            shell.recv(65535).decode("utf-8", errors="ignore")

            for cmd in commands:
                shell.send(f"{cmd}\n")
                time.sleep(0.1)
                output = shell.recv(65535).decode("utf-8", errors="ignore")
                log_entries.append(f"CMD: {cmd}")
                log_entries.append(f"OUTPUT: {output}")

            if self.deploy_save_enabled.get():
                save_cmd = self.deploy_save_command
                detect_str = self.deploy_save_detect
                start_time = time.time()
                detected = False
                while time.time() - start_time < 30:
                    shell.send(f"{save_cmd}\n")
                    time.sleep(0.5)
                    output = shell.recv(65535).decode("utf-8", errors="ignore")
                    log_entries.append(f"SAVE CHECK: {output}")
                    if detect_str in output:
                        detected = True
                        break
                    time.sleep(1)
                if not detected:
                    fail_reason = f"保存检测超时，未检测到 '{detect_str}'"
                    raise Exception(fail_reason)

            ssh.close()
            log_entries.append(f"SUCCESS {ip}")
            success = True
        except Exception as e:
            fail_reason = str(e)
            log_entries.append(f"FAILED {ip}: {fail_reason}")
            success = False

        with open(self.deploy_log_file, "a", encoding="utf-8") as lf:
            lf.write("\n".join(log_entries) + "\n\n")

        if success:
            with open(self.deploy_success_file, "a", encoding="utf-8") as sf:
                sf.write(f"{ip}\n")
        else:
            with open(self.deploy_fail_file, "a", encoding="utf-8") as ff:
                ff.write(f"{ip} - {fail_reason}\n")

        self.root.after(0, lambda: self._remove_right_ip(ip))

    def _remove_right_ip(self, ip):
        try:
            items = self.deploy_right_listbox.get(0, tk.END)
            for idx, item in enumerate(items):
                if item == ip:
                    self.deploy_right_listbox.delete(idx)
                    break
        except Exception:
            pass

    def on_deploy_finished(self):
        self.deploy_running = False
        self.deploy_btn_start.config(state="normal")
        self.deploy_btn_load.config(state="normal")
        self.deploy_btn_fields.config(state="normal")
        self.deploy_btn_template.config(state="normal")
        self.deploy_btn_back.config(state="normal")
        messagebox.showinfo("下发完成",
                            f"所有任务已处理完成。\n运行日志：{self.deploy_log_file}\n"
                            f"成功设备：{self.deploy_success_file}\n失败设备：{self.deploy_fail_file}")
