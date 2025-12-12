"""
可编辑字段组件
"""

import customtkinter as ctk
from typing import Optional, Callable, Any, List
from tkinter import messagebox

from ...utils.constants import Colors


class EditableField(ctk.CTkFrame):
    """可编辑字段组件"""

    def __init__(
        self,
        master,
        label: str,
        value: str = "-",
        field_type: str = "text",  # text, number, hex, select
        options: Optional[List[str]] = None,  # 用于 select 类型
        min_value: Optional[int] = None,
        max_value: Optional[int] = None,
        editable: bool = True,
        on_change: Optional[Callable[[str, Any], None]] = None,
        **kwargs
    ):
        super().__init__(master, fg_color="transparent", **kwargs)

        self.label_text = label
        self._value = value
        self.field_type = field_type
        self.options = options or []
        self.min_value = min_value
        self.max_value = max_value
        self.editable = editable
        self.on_change = on_change
        self._is_modified = False

        self.grid_columnconfigure(1, weight=1)
        self._setup_ui()

    def _setup_ui(self):
        """设置UI"""
        # 标签
        self.label = ctk.CTkLabel(
            self,
            text=f"{self.label_text}:",
            font=("Arial", 12),
            text_color=Colors.TEXT_SECONDARY,
            width=120,
            anchor="w"
        )
        self.label.grid(row=0, column=0, sticky="w", padx=(0, 10))

        # 值显示/编辑区域
        self.value_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.value_frame.grid(row=0, column=1, sticky="ew")
        self.value_frame.grid_columnconfigure(0, weight=1)

        self.value_label = ctk.CTkLabel(
            self.value_frame,
            text=self._value,
            font=("Arial", 12),
            text_color=Colors.TEXT,
            anchor="w"
        )
        self.value_label.grid(row=0, column=0, sticky="w")

        # 编辑按钮
        if self.editable:
            self.edit_btn = ctk.CTkButton(
                self.value_frame,
                text="Edit",
                width=50,
                height=24,
                font=("Arial", 10),
                fg_color=Colors.SECONDARY,
                hover_color=Colors.PRIMARY,
                command=self._on_edit
            )
            self.edit_btn.grid(row=0, column=1, sticky="e", padx=(10, 0))

        # 修改标记
        self.modified_indicator = ctk.CTkLabel(
            self.value_frame,
            text="*",
            font=("Arial", 14, "bold"),
            text_color=Colors.MODIFIED,
            width=15
        )
        self.modified_indicator.grid(row=0, column=2, sticky="e")
        self.modified_indicator.grid_remove()  # 初始隐藏

    def _on_edit(self):
        """编辑按钮点击"""
        if self.field_type == "select" and self.options:
            self._show_select_dialog()
        elif self.field_type == "hex":
            self._show_hex_dialog()
        elif self.field_type == "number":
            self._show_number_dialog()
        else:
            self._show_text_dialog()

    def _show_text_dialog(self):
        """显示文本编辑对话框"""
        dialog = EditDialog(
            self.winfo_toplevel(),
            title=f"编辑 {self.label_text}",
            current_value=self._value,
            on_save=self._on_value_changed
        )

    def _show_number_dialog(self):
        """显示数字编辑对话框"""
        dialog = NumberEditDialog(
            self.winfo_toplevel(),
            title=f"编辑 {self.label_text}",
            current_value=self._value,
            min_value=self.min_value,
            max_value=self.max_value,
            on_save=self._on_value_changed
        )

    def _show_hex_dialog(self):
        """显示十六进制编辑对话框"""
        dialog = HexEditDialog(
            self.winfo_toplevel(),
            title=f"编辑 {self.label_text}",
            current_value=self._value,
            on_save=self._on_value_changed
        )

    def _show_select_dialog(self):
        """显示选择对话框"""
        dialog = SelectDialog(
            self.winfo_toplevel(),
            title=f"选择 {self.label_text}",
            options=self.options,
            current_value=self._value,
            on_save=self._on_value_changed
        )

    def _on_value_changed(self, new_value: str):
        """值变化回调"""
        if new_value != self._value:
            self._value = new_value
            self.value_label.configure(text=new_value)
            self._is_modified = True
            self.modified_indicator.grid()

            if self.on_change:
                self.on_change(self.label_text, new_value)

    def set_value(self, value: str, is_modified: bool = False):
        """设置值"""
        self._value = value
        self.value_label.configure(text=value)
        self._is_modified = is_modified

        if is_modified:
            self.modified_indicator.grid()
        else:
            self.modified_indicator.grid_remove()

    def get_value(self) -> str:
        """获取值"""
        return self._value

    def is_modified(self) -> bool:
        """是否被修改"""
        return self._is_modified

    def clear_modified(self):
        """清除修改标记"""
        self._is_modified = False
        self.modified_indicator.grid_remove()


class EditDialog(ctk.CTkToplevel):
    """通用编辑对话框"""

    def __init__(self, parent, title: str, current_value: str, on_save: Callable[[str], None]):
        super().__init__(parent)

        self.title(title)
        self.geometry("350x150")
        self.resizable(False, False)

        self.current_value = current_value
        self.on_save = on_save

        self.transient(parent)
        self.grab_set()

        self._setup_ui()

    def _setup_ui(self):
        """设置UI"""
        # 输入框
        ctk.CTkLabel(self, text="新值:").pack(anchor="w", padx=20, pady=(20, 5))
        self.entry = ctk.CTkEntry(self, width=300)
        self.entry.pack(padx=20)
        self.entry.insert(0, self.current_value)
        self.entry.select_range(0, "end")
        self.entry.focus()
        self.entry.bind("<Return>", self._on_save)

        # 按钮
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=20)

        ctk.CTkButton(
            btn_frame,
            text="取消",
            fg_color=Colors.SECONDARY,
            width=100,
            command=self.destroy
        ).pack(side="left", expand=True)

        ctk.CTkButton(
            btn_frame,
            text="保存",
            width=100,
            command=self._on_save
        ).pack(side="right", expand=True)

    def _on_save(self, event=None):
        """保存"""
        value = self.entry.get()
        self.on_save(value)
        self.destroy()


class NumberEditDialog(ctk.CTkToplevel):
    """数字编辑对话框"""

    def __init__(
        self,
        parent,
        title: str,
        current_value: str,
        min_value: Optional[int],
        max_value: Optional[int],
        on_save: Callable[[str], None]
    ):
        super().__init__(parent)

        self.title(title)
        self.geometry("350x180")
        self.resizable(False, False)

        self.current_value = current_value
        self.min_value = min_value
        self.max_value = max_value
        self.on_save = on_save

        self.transient(parent)
        self.grab_set()

        self._setup_ui()

    def _setup_ui(self):
        """设置UI"""
        # 范围提示
        range_text = ""
        if self.min_value is not None and self.max_value is not None:
            range_text = f" ({self.min_value} - {self.max_value})"
        elif self.min_value is not None:
            range_text = f" (>= {self.min_value})"
        elif self.max_value is not None:
            range_text = f" (<= {self.max_value})"

        ctk.CTkLabel(self, text=f"新值{range_text}:").pack(anchor="w", padx=20, pady=(20, 5))

        # 输入框
        self.entry = ctk.CTkEntry(self, width=300)
        self.entry.pack(padx=20)

        try:
            # 尝试提取数字部分
            num_str = ''.join(c for c in self.current_value if c.isdigit() or c == '.')
            self.entry.insert(0, num_str)
        except:
            self.entry.insert(0, self.current_value)

        self.entry.select_range(0, "end")
        self.entry.focus()
        self.entry.bind("<Return>", self._on_save)

        # 错误提示
        self.error_label = ctk.CTkLabel(
            self,
            text="",
            font=("Arial", 10),
            text_color=Colors.DANGER
        )
        self.error_label.pack(anchor="w", padx=20)

        # 按钮
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=20)

        ctk.CTkButton(
            btn_frame,
            text="取消",
            fg_color=Colors.SECONDARY,
            width=100,
            command=self.destroy
        ).pack(side="left", expand=True)

        ctk.CTkButton(
            btn_frame,
            text="保存",
            width=100,
            command=self._on_save
        ).pack(side="right", expand=True)

    def _on_save(self, event=None):
        """保存"""
        try:
            value = int(self.entry.get())
            if self.min_value is not None and value < self.min_value:
                self.error_label.configure(text=f"值不能小于 {self.min_value}")
                return
            if self.max_value is not None and value > self.max_value:
                self.error_label.configure(text=f"值不能大于 {self.max_value}")
                return

            self.on_save(str(value))
            self.destroy()
        except ValueError:
            self.error_label.configure(text="请输入有效的数字")


class HexEditDialog(ctk.CTkToplevel):
    """十六进制编辑对话框"""

    def __init__(self, parent, title: str, current_value: str, on_save: Callable[[str], None]):
        super().__init__(parent)

        self.title(title)
        self.geometry("350x200")
        self.resizable(False, False)

        self.current_value = current_value
        self.on_save = on_save

        self.transient(parent)
        self.grab_set()

        self._setup_ui()

    def _setup_ui(self):
        """设置UI"""
        # 十六进制输入
        ctk.CTkLabel(self, text="十六进制值 (0x前缀可选):").pack(anchor="w", padx=20, pady=(20, 5))
        self.hex_entry = ctk.CTkEntry(self, width=300)
        self.hex_entry.pack(padx=20)
        self.hex_entry.insert(0, self.current_value)
        self.hex_entry.select_range(0, "end")
        self.hex_entry.focus()
        self.hex_entry.bind("<KeyRelease>", self._on_hex_change)
        self.hex_entry.bind("<Return>", self._on_save)

        # 十进制显示
        ctk.CTkLabel(self, text="十进制值:").pack(anchor="w", padx=20, pady=(10, 5))
        self.dec_label = ctk.CTkLabel(self, text="-", font=("Arial", 12))
        self.dec_label.pack(anchor="w", padx=20)

        self._on_hex_change(None)

        # 按钮
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=20)

        ctk.CTkButton(
            btn_frame,
            text="取消",
            fg_color=Colors.SECONDARY,
            width=100,
            command=self.destroy
        ).pack(side="left", expand=True)

        ctk.CTkButton(
            btn_frame,
            text="保存",
            width=100,
            command=self._on_save
        ).pack(side="right", expand=True)

    def _on_hex_change(self, event):
        """十六进制输入变化"""
        try:
            hex_str = self.hex_entry.get().strip()
            if hex_str.startswith("0x") or hex_str.startswith("0X"):
                hex_str = hex_str[2:]
            value = int(hex_str, 16)
            self.dec_label.configure(text=str(value))
        except ValueError:
            self.dec_label.configure(text="无效")

    def _on_save(self, event=None):
        """保存"""
        hex_str = self.hex_entry.get().strip()
        if not hex_str.startswith("0x") and not hex_str.startswith("0X"):
            hex_str = "0x" + hex_str
        self.on_save(hex_str)
        self.destroy()


class SelectDialog(ctk.CTkToplevel):
    """选择对话框"""

    def __init__(
        self,
        parent,
        title: str,
        options: List[str],
        current_value: str,
        on_save: Callable[[str], None]
    ):
        super().__init__(parent)

        self.title(title)
        self.geometry("350x300")
        self.resizable(False, False)

        self.options = options
        self.current_value = current_value
        self.on_save = on_save
        self.selected = current_value

        self.transient(parent)
        self.grab_set()

        self._setup_ui()

    def _setup_ui(self):
        """设置UI"""
        ctk.CTkLabel(self, text="选择一个选项:").pack(anchor="w", padx=20, pady=(20, 10))

        # 滚动列表
        self.scroll_frame = ctk.CTkScrollableFrame(self, width=290, height=180)
        self.scroll_frame.pack(padx=20, fill="both", expand=True)

        self.radio_var = ctk.StringVar(value=self.current_value)
        for option in self.options:
            rb = ctk.CTkRadioButton(
                self.scroll_frame,
                text=option,
                variable=self.radio_var,
                value=option
            )
            rb.pack(anchor="w", pady=2)

        # 按钮
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=20)

        ctk.CTkButton(
            btn_frame,
            text="取消",
            fg_color=Colors.SECONDARY,
            width=100,
            command=self.destroy
        ).pack(side="left", expand=True)

        ctk.CTkButton(
            btn_frame,
            text="选择",
            width=100,
            command=self._on_save
        ).pack(side="right", expand=True)

    def _on_save(self):
        """保存"""
        self.on_save(self.radio_var.get())
        self.destroy()
