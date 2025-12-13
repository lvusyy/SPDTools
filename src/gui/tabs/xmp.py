"""
XMP 选项卡
展示和编辑 XMP 配置
"""

import customtkinter as ctk
from typing import Optional, Dict, Any

from ..widgets.editable_field import EditableField
from ..widgets.xmp_edit_dialog import XMPEditDialog
from ...core.model import SPDDataModel, DataChangeEvent
from ...core.parser import DDR4Parser
from ...utils.constants import Colors, SPD_BYTES, MTB


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
        freq_label.pack(side="right", padx=(0, 10))

        # 编辑按钮
        edit_btn = ctk.CTkButton(
            title_frame,
            text="编辑",
            width=60,
            height=24,
            font=("Arial", 10),
            fg_color=Colors.PRIMARY,
            hover_color=Colors.HIGHLIGHT,
            command=lambda: self._on_edit_profile(profile_num, profile_data)
        )
        edit_btn.pack(side="right")

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

        # 添加创建 XMP 按钮
        create_frame = ctk.CTkFrame(self.profiles_container, fg_color="transparent")
        create_frame.grid(row=1, column=0, columnspan=2, pady=20)

        ctk.CTkButton(
            create_frame,
            text="创建 XMP Profile 1",
            width=180,
            fg_color=Colors.SUCCESS,
            hover_color=Colors.HIGHLIGHT,
            command=lambda: self._on_create_profile(1)
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            create_frame,
            text="创建 XMP Profile 2",
            width=180,
            fg_color=Colors.SUCCESS,
            hover_color=Colors.HIGHLIGHT,
            command=lambda: self._on_create_profile(2)
        ).pack(side="left", padx=10)

    def _on_edit_profile(self, profile_num: int, profile_data: Dict):
        """编辑 XMP Profile"""
        if not self.data_model.has_data:
            return

        # 打开编辑对话框
        XMPEditDialog(
            self.winfo_toplevel(),
            profile_num=profile_num,
            profile_data=profile_data,
            on_save=lambda data: self._write_xmp_profile(profile_num, data)
        )

    def _on_create_profile(self, profile_num: int):
        """创建新的 XMP Profile"""
        if not self.data_model.has_data:
            return

        # 使用默认值创建新 Profile
        default_data = {
            "frequency": 3200,
            "voltage": 1.350,
            "cl": 16,
            "trcd": 18,
            "trp": 18,
            "tras": 38
        }

        # 打开编辑对话框
        XMPEditDialog(
            self.winfo_toplevel(),
            profile_num=profile_num,
            profile_data=default_data,
            on_save=lambda data: self._write_xmp_profile(profile_num, data, is_new=True)
        )

    def _write_xmp_profile(self, profile_num: int, data: Dict, is_new: bool = False):
        """写入 XMP Profile 到 SPD 数据"""
        # 如果是新建 Profile，先初始化 XMP 头部
        if is_new:
            # 检查是否已有 XMP 头部
            xmp_header = self.data_model.get_byte(SPD_BYTES.XMP_HEADER)
            if xmp_header != 0x0C:
                # 初始化 XMP 头部
                self.data_model.set_byte(SPD_BYTES.XMP_HEADER, 0x0C)
                self.data_model.set_byte(SPD_BYTES.XMP_HEADER + 1, 0x4A)  # 'J'
                self.data_model.set_byte(SPD_BYTES.XMP_REVISION, 0x20)  # XMP 2.0

        # 计算 Profile 偏移
        profile_offset = SPD_BYTES.XMP_PROFILE1_START if profile_num == 1 else SPD_BYTES.XMP_PROFILE2_START

        # 频率 -> tCK (MTB)
        freq_mhz = data.get("frequency", 3200)
        tck_ps = 2000000 / freq_mhz  # 2000000 ps / MT/s
        tck_mtb = int(tck_ps / MTB)

        # 电压编码: 1.2V + (byte[5:0] × 5mV), bit7 = enabled
        voltage = data.get("voltage", 1.350)
        voltage_mv = int((voltage - 1.2) * 1000 / 5)  # Convert to 5mV units
        voltage_byte = 0x80 | (voltage_mv & 0x3F)  # Set bit 7 (enabled) + voltage

        # CL/tRCD/tRP/tRAS 时序
        cl = data.get("cl", 16)
        trcd_ns = data.get("trcd", 18)
        trp_ns = data.get("trp", 18)
        tras_ns = data.get("tras", 38)

        # 转换为 MTB
        trcd_mtb = int(trcd_ns * 1000 / MTB)
        trp_mtb = int(trp_ns * 1000 / MTB)
        tras_mtb = int(tras_ns * 1000 / MTB)

        # 写入 Profile 数据 (根据 XMP 2.0 规范)
        # Offset +0: 电压
        self.data_model.set_byte(profile_offset + 0, voltage_byte)

        # Offset +3: tCK (MTB)
        self.data_model.set_byte(profile_offset + 3, tck_mtb)

        # Offset +8: tAA (CL in MTB)
        taa_mtb = int(cl * tck_ps / MTB)
        self.data_model.set_byte(profile_offset + 8, taa_mtb)

        # Offset +9: tRCD (MTB)
        self.data_model.set_byte(profile_offset + 9, trcd_mtb)

        # Offset +10: tRP (MTB)
        self.data_model.set_byte(profile_offset + 10, trp_mtb)

        # Offset +11-12: tRAS (16-bit MTB)
        self.data_model.set_byte(profile_offset + 11, tras_mtb & 0xFF)
        self.data_model.set_byte(profile_offset + 12, (tras_mtb >> 8) & 0xFF)

        # 启用 Profile (设置 Profile 启用位)
        profile_enabled = self.data_model.get_byte(SPD_BYTES.XMP_PROFILE_ENABLED)
        if profile_num == 1:
            profile_enabled |= 0x01
        else:
            profile_enabled |= 0x02
        self.data_model.set_byte(SPD_BYTES.XMP_PROFILE_ENABLED, profile_enabled)

        # Refresh will be triggered automatically by data model observer
