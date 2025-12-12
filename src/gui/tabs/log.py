"""
日志选项卡
显示操作日志
"""

import customtkinter as ctk
from datetime import datetime
from typing import Optional

from ...utils.constants import Colors


class LogTab(ctk.CTkFrame):
    """日志选项卡"""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._setup_ui()

    def _setup_ui(self):
        """设置UI"""
        # 工具栏
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))

        ctk.CTkLabel(
            toolbar,
            text="操作日志",
            font=("Arial", 14, "bold")
        ).pack(side="left")

        ctk.CTkButton(
            toolbar,
            text="清空",
            width=60,
            fg_color=Colors.SECONDARY,
            command=self.clear
        ).pack(side="right")

        ctk.CTkButton(
            toolbar,
            text="导出",
            width=60,
            fg_color=Colors.SECONDARY,
            command=self._export_log
        ).pack(side="right", padx=(0, 10))

        # 日志文本框
        self.log_text = ctk.CTkTextbox(
            self,
            font=("Consolas", 11),
            fg_color="#1e1e1e",
            state="disabled"
        )
        self.log_text.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        # 配置标签
        self.log_text.tag_config("timestamp", foreground="#6A9955")
        self.log_text.tag_config("info", foreground=Colors.TEXT)
        self.log_text.tag_config("success", foreground=Colors.SUCCESS)
        self.log_text.tag_config("warning", foreground=Colors.WARNING)
        self.log_text.tag_config("error", foreground=Colors.DANGER)

    def log(self, message: str, level: str = "info"):
        """
        添加日志

        Args:
            message: 日志消息
            level: 日志级别 (info, success, warning, error)
        """
        self.log_text.configure(state="normal")

        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{timestamp}] ", "timestamp")
        self.log_text.insert("end", f"{message}\n", level)

        self.log_text.configure(state="disabled")
        self.log_text.see("end")

    def log_info(self, message: str):
        """信息日志"""
        self.log(message, "info")

    def log_success(self, message: str):
        """成功日志"""
        self.log(message, "success")

    def log_warning(self, message: str):
        """警告日志"""
        self.log(message, "warning")

    def log_error(self, message: str):
        """错误日志"""
        self.log(message, "error")

    def clear(self):
        """清空日志"""
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _export_log(self):
        """导出日志"""
        from tkinter import filedialog

        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfilename=f"spd_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )

        if path:
            content = self.log_text.get("1.0", "end")
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            self.log_success(f"日志已导出到: {path}")

    def get_content(self) -> str:
        """获取日志内容"""
        return self.log_text.get("1.0", "end")
