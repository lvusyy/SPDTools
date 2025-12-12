"""
时序选项卡
展示和编辑内存时序参数
"""

import customtkinter as ctk
from typing import Optional, Dict, Any

from ..widgets.editable_field import EditableField
from ...core.model import SPDDataModel, DataChangeEvent
from ...core.parser import DDR4Parser
from ...utils.constants import Colors


class TimingTab(ctk.CTkFrame):
    """时序选项卡"""

    def __init__(self, master, data_model: SPDDataModel, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self.data_model = data_model
        self.fields = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._setup_ui()
        self.data_model.add_observer(self._on_data_changed)

    def _setup_ui(self):
        """设置UI"""
        # 顶部：主时序显示
        header_frame = ctk.CTkFrame(self, fg_color=Colors.CARD_BG, corner_radius=10)
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=10)

        ctk.CTkLabel(
            header_frame,
            text="主时序参数",
            font=("Arial", 14, "bold")
        ).pack(anchor="w", padx=15, pady=(12, 5))

        self.main_timing_label = ctk.CTkLabel(
            header_frame,
            text="CL--",
            font=("Consolas", 32, "bold"),
            text_color=Colors.HIGHLIGHT
        )
        self.main_timing_label.pack(anchor="w", padx=15, pady=(0, 5))

        self.timing_detail_label = ctk.CTkLabel(
            header_frame,
            text="@ - MT/s",
            font=("Arial", 12),
            text_color=Colors.TEXT_SECONDARY
        )
        self.timing_detail_label.pack(anchor="w", padx=15, pady=(0, 12))

        # 左侧：基本时序
        left_frame = ctk.CTkFrame(self, fg_color=Colors.CARD_BG, corner_radius=10)
        left_frame.grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=10)
        left_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            left_frame,
            text="基本时序 (ns)",
            font=("Arial", 13, "bold")
        ).grid(row=0, column=0, sticky="w", padx=15, pady=(12, 8))

        basic_timings = [
            ("tCK (时钟周期)", "tCK"),
            ("tAA (CAS Latency)", "tAA"),
            ("tRCD (RAS to CAS)", "tRCD"),
            ("tRP (Row Precharge)", "tRP"),
            ("tRAS (Active to Precharge)", "tRAS"),
            ("tRC (Row Cycle)", "tRC"),
        ]

        for i, (label, key) in enumerate(basic_timings):
            field = EditableField(
                left_frame,
                label=label,
                value="-",
                field_type="text",
                editable=False
            )
            field.grid(row=i + 1, column=0, sticky="ew", padx=15, pady=3)
            self.fields[key] = field

        # 右侧：高级时序
        right_frame = ctk.CTkFrame(self, fg_color=Colors.CARD_BG, corner_radius=10)
        right_frame.grid(row=1, column=1, sticky="nsew", padx=(5, 10), pady=10)
        right_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            right_frame,
            text="高级时序 (ns)",
            font=("Arial", 13, "bold")
        ).grid(row=0, column=0, sticky="w", padx=15, pady=(12, 8))

        advanced_timings = [
            ("tRFC1 (Refresh Recovery)", "tRFC1"),
            ("tFAW (Four Activate Window)", "tFAW"),
            ("tRRD_S (Act to Act, diff BG)", "tRRD_S"),
            ("tRRD_L (Act to Act, same BG)", "tRRD_L"),
            ("tCCD_L (CAS to CAS, same BG)", "tCCD_L"),
        ]

        for i, (label, key) in enumerate(advanced_timings):
            field = EditableField(
                right_frame,
                label=label,
                value="-",
                field_type="text",
                editable=False
            )
            field.grid(row=i + 1, column=0, sticky="ew", padx=15, pady=3)
            self.fields[key] = field

        # 底部：支持的 CAS Latency
        bottom_frame = ctk.CTkFrame(self, fg_color=Colors.CARD_BG, corner_radius=10)
        bottom_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10))

        ctk.CTkLabel(
            bottom_frame,
            text="支持的 CAS Latency",
            font=("Arial", 13, "bold")
        ).pack(anchor="w", padx=15, pady=(12, 8))

        self.cl_label = ctk.CTkLabel(
            bottom_frame,
            text="-",
            font=("Consolas", 11),
            text_color=Colors.TEXT
        )
        self.cl_label.pack(anchor="w", padx=15, pady=(0, 12))

    def _on_data_changed(self, event: DataChangeEvent):
        """数据变更回调"""
        self.refresh()

    def refresh(self):
        """刷新显示"""
        if not self.data_model.has_data:
            self._show_no_data()
            return

        parser = DDR4Parser(self.data_model.data)
        info = parser.to_dict()

        if "error" in info:
            self._show_no_data()
            return

        # 更新主时序
        self.main_timing_label.configure(text=info.get("timing_string", "CL--"))
        speed = info.get("speed_grade", 0)
        self.timing_detail_label.configure(text=f"@ {speed} MT/s" if speed else "@ - MT/s")

        # 更新时序字段
        timings = info.get("timings", {})
        for key, field in self.fields.items():
            if key in timings:
                field.set_value(str(timings[key]))
            elif key == "tFAW":
                # 需要额外计算
                timing_obj = parser.parse_timings()
                field.set_value(f"{timing_obj.tFAW:.3f} ns")
            elif key == "tRRD_S":
                timing_obj = parser.parse_timings()
                field.set_value(f"{timing_obj.tRRD_S:.3f} ns")
            elif key == "tRRD_L":
                timing_obj = parser.parse_timings()
                field.set_value(f"{timing_obj.tRRD_L:.3f} ns")
            elif key == "tCCD_L":
                timing_obj = parser.parse_timings()
                field.set_value(f"{timing_obj.tCCD_L:.3f} ns")

        # 更新支持的 CL
        supported_cl = info.get("supported_cl", [])
        if supported_cl:
            cl_str = ", ".join(f"CL{cl}" for cl in sorted(supported_cl))
            self.cl_label.configure(text=cl_str)
        else:
            self.cl_label.configure(text="-")

    def _show_no_data(self):
        """显示无数据状态"""
        self.main_timing_label.configure(text="CL--")
        self.timing_detail_label.configure(text="@ - MT/s")

        for field in self.fields.values():
            field.set_value("-")

        self.cl_label.configure(text="-")
