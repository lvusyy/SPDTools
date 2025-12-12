"""
信息卡片组件
用于在概览页面展示内存信息
"""

import customtkinter as ctk
from typing import Optional, Callable

from ...utils.constants import Colors


class InfoCard(ctk.CTkFrame):
    """信息卡片组件"""

    def __init__(
        self,
        master,
        title: str,
        value: str = "-",
        subtitle: str = "",
        icon: str = "",
        width: int = 200,
        height: int = 100,
        editable: bool = False,
        on_edit: Optional[Callable] = None,
        **kwargs
    ):
        super().__init__(
            master,
            width=width,
            height=height,
            corner_radius=10,
            fg_color=Colors.CARD_BG,
            **kwargs
        )

        self.title = title
        self._value = value
        self.editable = editable
        self.on_edit = on_edit

        self.grid_columnconfigure(0, weight=1)
        self._setup_ui(title, value, subtitle, icon)

    def _setup_ui(self, title: str, value: str, subtitle: str, icon: str):
        """设置UI"""
        # 标题行
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=(12, 0))
        header_frame.grid_columnconfigure(0, weight=1)

        # 图标 + 标题
        if icon:
            icon_label = ctk.CTkLabel(
                header_frame,
                text=icon,
                font=("Arial", 16),
                text_color=Colors.TEXT_SECONDARY
            )
            icon_label.grid(row=0, column=0, sticky="w")

        title_label = ctk.CTkLabel(
            header_frame,
            text=title,
            font=("Arial", 12),
            text_color=Colors.TEXT_SECONDARY
        )
        title_label.grid(row=0, column=0 if not icon else 1, sticky="w", padx=(4 if icon else 0, 0))

        # 编辑按钮
        if self.editable:
            edit_btn = ctk.CTkButton(
                header_frame,
                text="Edit",
                width=40,
                height=20,
                font=("Arial", 10),
                fg_color=Colors.SECONDARY,
                hover_color=Colors.PRIMARY,
                command=self._on_edit_click
            )
            edit_btn.grid(row=0, column=2, sticky="e")

        # 主值
        self.value_label = ctk.CTkLabel(
            self,
            text=value,
            font=("Arial", 22, "bold"),
            text_color=Colors.TEXT
        )
        self.value_label.grid(row=1, column=0, sticky="w", padx=15, pady=(5, 0))

        # 副标题
        if subtitle:
            self.subtitle_label = ctk.CTkLabel(
                self,
                text=subtitle,
                font=("Arial", 11),
                text_color=Colors.TEXT_SECONDARY
            )
            self.subtitle_label.grid(row=2, column=0, sticky="w", padx=15, pady=(2, 12))
        else:
            self.subtitle_label = None

    def _on_edit_click(self):
        """编辑按钮点击"""
        if self.on_edit:
            self.on_edit(self.title)

    def set_value(self, value: str, subtitle: str = None):
        """更新值"""
        self._value = value
        self.value_label.configure(text=value)
        if subtitle is not None and self.subtitle_label:
            self.subtitle_label.configure(text=subtitle)

    def get_value(self) -> str:
        """获取当前值"""
        return self._value

    def highlight(self, color: str = Colors.MODIFIED):
        """高亮显示（表示已修改）"""
        self.configure(border_width=2, border_color=color)

    def clear_highlight(self):
        """清除高亮"""
        self.configure(border_width=0)


class LargeInfoCard(ctk.CTkFrame):
    """大型信息卡片，用于展示详细信息列表"""

    def __init__(
        self,
        master,
        title: str,
        width: int = 400,
        min_height: int = 150,
        **kwargs
    ):
        super().__init__(
            master,
            width=width,
            corner_radius=10,
            fg_color=Colors.CARD_BG,
            **kwargs
        )

        self.title = title
        self.items = []

        self.grid_columnconfigure(0, weight=1)
        self._setup_ui(title)

    def _setup_ui(self, title: str):
        """设置UI"""
        # 标题
        title_label = ctk.CTkLabel(
            self,
            text=title,
            font=("Arial", 14, "bold"),
            text_color=Colors.TEXT
        )
        title_label.grid(row=0, column=0, sticky="w", padx=15, pady=(12, 8))

        # 分隔线
        separator = ctk.CTkFrame(self, height=1, fg_color=Colors.SECONDARY)
        separator.grid(row=1, column=0, sticky="ew", padx=15)

        # 内容区域
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.grid(row=2, column=0, sticky="nsew", padx=15, pady=(8, 12))
        self.content_frame.grid_columnconfigure(1, weight=1)

    def add_item(self, label: str, value: str, editable: bool = False, on_edit: Optional[Callable] = None):
        """添加一行信息"""
        row = len(self.items)

        label_widget = ctk.CTkLabel(
            self.content_frame,
            text=f"{label}:",
            font=("Arial", 12),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w"
        )
        label_widget.grid(row=row, column=0, sticky="w", pady=3)

        value_widget = ctk.CTkLabel(
            self.content_frame,
            text=value,
            font=("Arial", 12),
            text_color=Colors.TEXT,
            anchor="w"
        )
        value_widget.grid(row=row, column=1, sticky="w", padx=(10, 0), pady=3)

        item = {
            "label": label,
            "label_widget": label_widget,
            "value_widget": value_widget,
            "editable": editable,
            "on_edit": on_edit
        }

        if editable and on_edit:
            edit_btn = ctk.CTkButton(
                self.content_frame,
                text="Edit",
                width=40,
                height=20,
                font=("Arial", 10),
                fg_color=Colors.SECONDARY,
                hover_color=Colors.PRIMARY,
                command=lambda: on_edit(label)
            )
            edit_btn.grid(row=row, column=2, sticky="e", padx=(5, 0), pady=3)
            item["edit_btn"] = edit_btn

        self.items.append(item)

    def update_item(self, label: str, value: str):
        """更新指定项的值"""
        for item in self.items:
            if item["label"] == label:
                item["value_widget"].configure(text=value)
                break

    def clear_items(self):
        """清空所有项"""
        for item in self.items:
            item["label_widget"].destroy()
            item["value_widget"].destroy()
            if "edit_btn" in item:
                item["edit_btn"].destroy()
        self.items.clear()


class TimingCard(ctk.CTkFrame):
    """时序信息卡片"""

    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            corner_radius=10,
            fg_color=Colors.CARD_BG,
            **kwargs
        )

        self.grid_columnconfigure(0, weight=1)
        self._setup_ui()

    def _setup_ui(self):
        """设置UI"""
        # 标题
        title_label = ctk.CTkLabel(
            self,
            text="时序参数",
            font=("Arial", 14, "bold"),
            text_color=Colors.TEXT
        )
        title_label.grid(row=0, column=0, sticky="w", padx=15, pady=(12, 8))

        # 主时序显示
        self.timing_label = ctk.CTkLabel(
            self,
            text="CL--",
            font=("Consolas", 28, "bold"),
            text_color=Colors.HIGHLIGHT
        )
        self.timing_label.grid(row=1, column=0, sticky="w", padx=15, pady=5)

        # 详细时序
        self.detail_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.detail_frame.grid(row=2, column=0, sticky="ew", padx=15, pady=(5, 12))

        self.timing_details = {}
        timing_names = ["tAA", "tRCD", "tRP", "tRAS", "tRC", "tRFC1"]
        for i, name in enumerate(timing_names):
            col = i % 3
            row = i // 3

            frame = ctk.CTkFrame(self.detail_frame, fg_color="transparent")
            frame.grid(row=row, column=col, sticky="w", padx=(0, 20), pady=2)

            name_label = ctk.CTkLabel(
                frame,
                text=f"{name}:",
                font=("Arial", 10),
                text_color=Colors.TEXT_SECONDARY
            )
            name_label.pack(side="left")

            value_label = ctk.CTkLabel(
                frame,
                text="-",
                font=("Arial", 10),
                text_color=Colors.TEXT
            )
            value_label.pack(side="left", padx=(4, 0))

            self.timing_details[name] = value_label

    def set_timings(self, timing_string: str, details: dict):
        """设置时序信息"""
        self.timing_label.configure(text=timing_string)

        for name, widget in self.timing_details.items():
            if name in details:
                widget.configure(text=details[name])
