# main.py
import tkinter as tk
from tkinter import ttk
import webbrowser
import os

from tools.generator import ConfigGenerator
from tools.deploy import ConfigDeployer

# https://github.com/ocean4893/network-config-manager
class MainApp:
    def __init__(self, root):
        self.root = root
        self.root.version = "8.1"
        self.root.author = "OCEAN&DeepseekV4"
        self.root.title(f"网络设备综合配置管理器{self.root.version} - WriteBy {self.root.author}")
        self.root.geometry("900x650")
        self.root.resizable(True, True)

        bottom_frame = ttk.Frame(root)
        bottom_frame.pack(side="bottom", fill="x")
        link_label = ttk.Label(
            bottom_frame,
            text="https://github.com/ocean4893/network-config-manager",
            foreground="blue",
            cursor="hand2",
            font=("Helvetica", 10, "underline")
        )
        link_label.pack(pady=5)
        link_label.bind(
            "<Button-1>",
            lambda e: webbrowser.open_new("https://github.com/ocean4893/network-config-manager")
        )

        # 主菜单框架（整体居中）
        self.main_frame = ttk.Frame(self.root, padding=20)
        self.main_frame.pack(expand=True, fill="both")

        content_frame = ttk.Frame(self.main_frame)
        content_frame.pack(expand=True)

        # 标题
        main_title_label = ttk.Label(
            content_frame,
            text=f"网络设备综合配置管理器{self.root.version} - WriteBy {self.root.author}",
            font=("Helvetica", 24, "bold")
        )
        main_title_label.pack(pady=(0, 20))

        # 免责声明
        disclaimer_label = ttk.Label(
            content_frame,
            text="程序全部开源，无导出程序，运行代码与功能则代表你已阅读'免责声明.md'并同意相关条款，若不同意请立即关闭程序",
            font=("Helvetica", 10, "bold")
        )
        disclaimer_label.pack(pady=(0, 40))

        # 按钮
        btn_generate = ttk.Button(content_frame, text="配置批量生成",
                                  width=25, command=self.show_generator)
        btn_generate.pack(pady=15)

        btn_deploy = ttk.Button(content_frame, text="配置批量生成下发",
                                width=25, command=self.show_deploy)
        btn_deploy.pack(pady=15)

        ttk.Label(content_frame, text="更多功能开发中...", foreground="gray").pack(pady=20)

        # ---- 加入我们区域（放在下方） ----
        join_label = ttk.Label(
            content_frame,
            text="加入我们，共同开发！",
            font=("Helvetica", 12, "bold")
        )
        join_label.pack(pady=(20, 10))  # 上方多一些间距

        self._load_image(content_frame, "picture/qq.jpg")

        # 实例化功能模块
        self.generator = ConfigGenerator(self.root, back_callback=self.show_main)
        self.deployer = ConfigDeployer(self.root, back_callback=self.show_main)

    def _load_image(self, parent, img_path):
        """在 parent 组件中加载并显示图片，如果失败则显示提示文字"""
        try:
            from PIL import Image, ImageTk
            if os.path.exists(img_path):
                img = Image.open(img_path)
                img = img.resize((150, 150), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                img_label = ttk.Label(parent, image=photo)
                img_label.image = photo  # 保持引用
                img_label.pack()
            else:
                ttk.Label(parent, text="图片未找到", foreground="red").pack()
        except ImportError:
            ttk.Label(parent, text="缺少PIL库，无法显示图片", foreground="red").pack()
        except Exception as e:
            ttk.Label(parent, text=f"图片加载失败: {e}", foreground="red").pack()

    def show_main(self):
        self.generator.hide_page()
        self.deployer.hide_page()
        self.main_frame.pack(expand=True, fill="both")

    def show_generator(self):
        self.main_frame.pack_forget()
        self.generator.show_page()

    def show_deploy(self):
        self.main_frame.pack_forget()
        self.deployer.show_page()


if __name__ == "__main__":
    root = tk.Tk()
    app = MainApp(root)
    root.mainloop()