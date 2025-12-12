"""
XMP 选项卡
展示和编辑 XMP 配置
"""

import customtkinter as ctk
from typing import Optional, Dict, Any

from ..widgets.editable_field import EditableField
from ...core.model import SPDDataModel, DataChangeEvent
from ...core.parser import DDR4Parser
from ...utils.constants import Colors


class XMPTab(ctk.CTkFrame):
    """XMP 选项卡"""

    def __init__(self, master, data_model: SPDDataModel, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self.data_model = data_model
        self.profile_frames = []

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._setup_ui()
        self.data_model.add_observer(self._on_data_changed)

    def _setup_ui(self):
        """设置UI"""
        # 头部：XMP 状态
        header_frame = ctk.CTkFrame(self, fg_color=Colors.CARD_BG, corner_radius=10)
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        header_inner = ctk.CTkFrame(header_frame, fg_color="transparent")
        header_inner.pack(fill="x", padx=15, pady=12)

        ctk.CTkLabel(
            header_inner,
            text="XMP 状态",
            font=("Arial", 14, "bold")
        ).pack(side="left")

        self.xmp_status_label = ctk.CTkLabel(
            header_inner,
            text="未知",
            font=("Arial", 12),
            text_color=Colors.TEXT_SECONDARY
        )
        self.xmp_status_label.pack(side="left", padx=(20, 0))

        self.xmp_version_label = ctk.CTkLabel(
            header_inner,
            text="",
            font=("Arial", 11),
            text_color=Colors.TEXT_SECONDARY
        )
        self.xmp_version_label.pack(side="right")

        # Profile 容器
        self.profiles_container = ctk.CTkFrame(self, fg_color="transparent")
        self.profiles_container.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.profiles_container.grid_columnconfigure(0, weight=1)
        self.profiles_container.grid_columnconfigure(1, weight=1)

        # 无 XMP 提示
        self.no_xmp_label = ctk.CTkLabel(
            self.profiles_container,
            text="此内存不支持 XMP 或未检测到 XMP 配置",
            font=("Arial", 12),
            text_color=Colors.TEXT_SECONDARY
        )
        self.no_xmp_label.grid(row=0, column=0, columnspan=2, pady=50)

    def _create_profile_frame(self, profile_num: int, profile_data: Dict) -> ctk.CTkFrame:
        """创建 Profile 显示框架"""
        frame = ctk.CTkFrame(self.profiles_container, fg_color=Colors.CARD_BG, corner_radius=10)

        # 标题
        title_frame = ctk.CTkFrame(frame, fg_color="transparent")
        title_frame.pack(fill="x", padx=15, pady=(12, 8))

        ctk.CTkLabel(
            title_frame,
            text=f"Profile {profile_num}",
            font=("Arial", 14, "bold")
        ).pack(side="left")

        # 频率标签
        freq = profile_data.get("frequency", 0)
        freq_label = ctk.CTkLabel(
            title_frame,
            text=f"{freq} MT/s",
            font=("Arial", 12, "bold"),
            text_color=Colors.HIGHLIGHT
        )
        freq_label.pack(side="right")

        # 分隔线
        separator = ctk.CTkFrame(frame, height=1, fg_color=Colors.SECONDARY)
        separator.pack(fill="x", padx=15)

        # 内容
        content_frame = ctk.CTkFrame(frame, fg_color="transparent")
        content_frame.pack(fill="x", padx=15, pady=10)
        content_frame.grid_columnconfigure(1, weight=1)

        # 参数列表
        params = [
            ("频率", f"{profile_data.get('frequency', '-')} MT/s"),
            ("电压", f"{profile_data.get('voltage', 0):.3f}V"),
            ("时序", profile_data.get("timings", "-")),
        ]

        for i, (label, value) in enumerate(params):
            ctk.CTkLabel(
                content_frame,
                text=f"{label}:",
                font=("Arial", 11),
                text_color=Colors.TEXT_SECONDARY
            ).grid(row=i, column=0, sticky="w", pady=3)

            ctk.CTkLabel(
                content_frame,
                text=value,
                font=("Arial", 11),
                text_color=Colors.TEXT
            ).grid(row=i, column=1, sticky="w", padx=(10, 0), pady=3)

        return frame

    def _on_data_changed(self, event: DataChangeEvent):
        """数据变更回调"""
        self.refresh()

    def refresh(self):
        """刷新显示"""
        # 清除旧的 profile 框架
        for frame in self.profile_frames:
            frame.destroy()
        self.profile_frames.clear()

        if not self.data_model.has_data:
            self._show_no_xmp()
            return

        parser = DDR4Parser(self.data_model.data)
        info = parser.to_dict()

        if "error" in info:
            self._show_no_xmp()
            return

        xmp = info.get("xmp", {})

        if not xmp.get("supported"):
            self._show_no_xmp()
            return

        # 显示 XMP 支持
        self.no_xmp_label.grid_remove()

        self.xmp_status_label.configure(
            text="支持",
            text_color=Colors.SUCCESS
        )
        self.xmp_version_label.configure(
            text=f"XMP {xmp.get('version', '-')}"
        )

        # 创建 Profile 框架
        profiles = xmp.get("profiles", [])
        for i, profile in enumerate(profiles):
            profile_frame = self._create_profile_frame(i + 1, profile)
            profile_frame.grid(row=0, column=i, sticky="nsew", padx=5, pady=5)
            self.profile_frames.append(profile_frame)

    def _show_no_xmp(self):
        """显示无 XMP 状态"""
        self.xmp_status_label.configure(
            text="不支持",
            text_color=Colors.TEXT_SECONDARY
        )
        self.xmp_version_label.configure(text="")
        self.no_xmp_label.grid()
