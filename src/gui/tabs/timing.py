"""
时序选项卡
展示和编辑内存时序参数
"""

import customtkinter as ctk
from typing import Optional, Dict, Any

from ..widgets.editable_field import EditableField
from ..widgets.timing_edit_dialog import TimingEditDialog
from ...core.model import SPDDataModel, DataChangeEvent
from ...core.parser import DDR4Parser
from ...utils.constants import Colors, SPD_BYTES, MTB, FTB


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
            # Create custom clickable field for timing editing
            field_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
            field_frame.grid(row=i + 1, column=0, sticky="ew", padx=15, pady=3)
            field_frame.grid_columnconfigure(1, weight=1)

            # Label
            label_widget = ctk.CTkLabel(
                field_frame,
                text=f"{label}:",
                font=("Arial", 12),
                text_color=Colors.TEXT_SECONDARY,
                width=200,
                anchor="w"
            )
            label_widget.grid(row=0, column=0, sticky="w")

            # Value label
            value_label = ctk.CTkLabel(
                field_frame,
                text="-",
                font=("Arial", 12),
                text_color=Colors.TEXT,
                anchor="w"
            )
            value_label.grid(row=0, column=1, sticky="w", padx=(10, 0))

            # Edit button
            edit_btn = ctk.CTkButton(
                field_frame,
                text="Edit",
                width=50,
                height=24,
                font=("Arial", 10),
                fg_color=Colors.SECONDARY,
                hover_color=Colors.PRIMARY,
                command=lambda k=key, lbl=label: self._on_edit_timing(k, lbl)
            )
            edit_btn.grid(row=0, column=2, sticky="e", padx=(10, 0))

            # Store reference
            self.fields[key] = {"label": value_label, "button": edit_btn}

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
            ("tRFC2 (Refresh Recovery 2x)", "tRFC2"),
            ("tRFC4 (Refresh Recovery 4x)", "tRFC4"),
            ("tFAW (Four Activate Window)", "tFAW"),
            ("tRRD_S (Act to Act, diff BG)", "tRRD_S"),
            ("tRRD_L (Act to Act, same BG)", "tRRD_L"),
            ("tCCD_L (CAS to CAS, same BG)", "tCCD_L"),
            ("tWR (Write Recovery)", "tWR"),
            ("tWTR_S (Write to Read, diff BG)", "tWTR_S"),
            ("tWTR_L (Write to Read, same BG)", "tWTR_L"),
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
        for key in ["tCK", "tAA", "tRCD", "tRP", "tRAS", "tRC"]:
            if key in self.fields:
                field = self.fields[key]
                if isinstance(field, dict) and "label" in field:
                    # New format with custom layout
                    if key in timings:
                        field["label"].configure(text=str(timings[key]))
                else:
                    # Old EditableField format (for advanced timings)
                    if key in timings:
                        field.set_value(str(timings[key]))

        # Update advanced timings (still using EditableField)
        timing_obj = parser.parse_timings()
        if "tRFC1" in self.fields:
            self.fields["tRFC1"].set_value(f"{timing_obj.tRFC1:.1f} ns")
        if "tRFC2" in self.fields:
            self.fields["tRFC2"].set_value(f"{timing_obj.tRFC2:.1f} ns")
        if "tRFC4" in self.fields:
            self.fields["tRFC4"].set_value(f"{timing_obj.tRFC4:.1f} ns")
        if "tFAW" in self.fields:
            self.fields["tFAW"].set_value(f"{timing_obj.tFAW:.3f} ns")
        if "tRRD_S" in self.fields:
            self.fields["tRRD_S"].set_value(f"{timing_obj.tRRD_S:.3f} ns")
        if "tRRD_L" in self.fields:
            self.fields["tRRD_L"].set_value(f"{timing_obj.tRRD_L:.3f} ns")
        if "tCCD_L" in self.fields:
            self.fields["tCCD_L"].set_value(f"{timing_obj.tCCD_L:.3f} ns")
        if "tWR" in self.fields:
            self.fields["tWR"].set_value(f"{timing_obj.tWR:.3f} ns")
        if "tWTR_S" in self.fields:
            self.fields["tWTR_S"].set_value(f"{timing_obj.tWTR_S:.3f} ns")
        if "tWTR_L" in self.fields:
            self.fields["tWTR_L"].set_value(f"{timing_obj.tWTR_L:.3f} ns")

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

        for key, field in self.fields.items():
            if isinstance(field, dict) and "label" in field:
                field["label"].configure(text="-")
            else:
                field.set_value("-")

        self.cl_label.configure(text="-")

    def _on_edit_timing(self, key: str, label: str):
        """编辑时序参数"""
        if not self.data_model.has_data:
            return

        # 获取当前值
        field = self.fields.get(key)
        if not field or not isinstance(field, dict):
            return

        current_text = field["label"].cget("text")
        try:
            # 提取数值部分 (e.g., "13.500 ns" -> 13.500)
            current_value = float(current_text.split()[0])
        except (ValueError, IndexError):
            current_value = 0.0

        # 打开编辑对话框
        TimingEditDialog(
            self.winfo_toplevel(),
            param_name=key,
            param_label=label,
            current_value_ns=current_value,
            on_save=lambda v: self._write_timing(key, v)
        )

    def _write_timing(self, key: str, value_ns: float):
        """写入时序参数到 SPD 数据"""
        value_ps = value_ns * 1000
        mtb_value = int(value_ps / MTB)
        ftb_value = int((value_ps - mtb_value * MTB) / FTB)

        # 将 FTB 转换为有符号字节 (-128 到 127)
        if ftb_value > 127:
            ftb_value = ftb_value - 256
        elif ftb_value < -128:
            ftb_value = ftb_value + 256
        ftb_byte = ftb_value & 0xFF

        if key == "tCK":
            self.data_model.set_byte(SPD_BYTES.TCK_MIN, mtb_value)
            self.data_model.set_byte(SPD_BYTES.TCK_MIN_FTB, ftb_byte)

        elif key == "tAA":
            self.data_model.set_byte(SPD_BYTES.TAA_MIN, mtb_value)
            self.data_model.set_byte(SPD_BYTES.TAA_MIN_FTB, ftb_byte)

        elif key == "tRCD":
            self.data_model.set_byte(SPD_BYTES.TRCD_MIN, mtb_value)
            self.data_model.set_byte(SPD_BYTES.TRCD_MIN_FTB, ftb_byte)

        elif key == "tRP":
            self.data_model.set_byte(SPD_BYTES.TRP_MIN, mtb_value)
            self.data_model.set_byte(SPD_BYTES.TRP_MIN_FTB, ftb_byte)

        elif key == "tRAS":
            # tRAS uses high nibble of byte 27 + full byte 28
            high_nibble = (mtb_value >> 8) & 0x0F
            low_byte = mtb_value & 0xFF
            current_27 = self.data_model.get_byte(SPD_BYTES.TRAS_TRC_HIGH)
            new_27 = (current_27 & 0xF0) | high_nibble  # Keep tRC high nibble
            self.data_model.set_byte(SPD_BYTES.TRAS_TRC_HIGH, new_27)
            self.data_model.set_byte(SPD_BYTES.TRAS_MIN_LOW, low_byte)

        elif key == "tRC":
            # tRC uses high nibble of byte 27 + full byte 29 + FTB
            high_nibble = (mtb_value >> 8) & 0x0F
            low_byte = mtb_value & 0xFF
            current_27 = self.data_model.get_byte(SPD_BYTES.TRAS_TRC_HIGH)
            new_27 = (current_27 & 0x0F) | (high_nibble << 4)  # Keep tRAS high nibble
            self.data_model.set_byte(SPD_BYTES.TRAS_TRC_HIGH, new_27)
            self.data_model.set_byte(SPD_BYTES.TRC_MIN_LOW, low_byte)
            self.data_model.set_byte(SPD_BYTES.TRC_MIN_FTB, ftb_byte)

        # Refresh will be triggered automatically by data model observer
