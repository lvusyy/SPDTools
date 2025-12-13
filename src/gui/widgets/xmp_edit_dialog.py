"""
XMP 配置文件编辑/创建对话框
"""
import customtkinter as ctk
from typing import Dict, Callable, Optional
from ...utils.constants import Colors, MTB
from ...utils.timing_validator import validate_timing, RiskLevel, RISK_COLORS


class XMPEditDialog(ctk.CTkToplevel):
    """XMP 配置文件编辑/创建对话框"""

    def __init__(
        self,
        parent,
        profile_num: int,
        existing_data: Optional[Dict] = None,
        on_save: Callable[[int, Dict], None] = None
    ):
        """
        Args:
            profile_num: 配置文件编号 (1 或 2)
            existing_data: 现有数据 (None 表示创建新配置)
            on_save: 保存回调 callback(profile_num, data_dict)
        """
        super().__init__(parent)

        self.profile_num = profile_num
        self.existing_data = existing_data
        self.on_save = on_save
        self.is_create = existing_data is None

        title = f"创建 XMP Profile {profile_num}" if self.is_create else f"编辑 XMP Profile {profile_num}"
        self.title(title)
        self.geometry("480x560")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._setup_ui()
        self._update_preview()

    def _setup_ui(self):
        """设置UI"""
        # 头部
        header_text = "创建新的 XMP 配置文件" if self.is_create else "编辑 XMP 配置文件"
        ctk.CTkLabel(
            self,
            text=header_text,
            font=("Arial", 16, "bold")
        ).pack(pady=(20, 5))

        ctk.CTkLabel(
            self,
            text=f"Profile {self.profile_num}",
            font=("Arial", 12),
            text_color=Colors.HIGHLIGHT
        ).pack(pady=(0, 15))

        # 表单字段
        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="x", padx=30, pady=10)

        self.fields = {}

        # 频率 (MT/s)
        self._add_field(
            form, "frequency", "频率 (MT/s)",
            default=self.existing_data.get("frequency", 3200) if self.existing_data else 3200,
            min_val=1600, max_val=6000, row=0
        )

        # 电压 (V)
        self._add_field(
            form, "voltage", "电压 (V)",
            default=self.existing_data.get("voltage", 1.35) if self.existing_data else 1.35,
            min_val=1.10, max_val=1.50, row=1, is_float=True
        )

        # CL
        self._add_field(
            form, "CL", "CAS Latency (CL)",
            default=self.existing_data.get("CL", 16) if self.existing_data else 16,
            min_val=10, max_val=40, row=2
        )

        # tRCD
        self._add_field(
            form, "tRCD", "tRCD (cycles)",
            default=self.existing_data.get("tRCD", 18) if self.existing_data else 18,
            min_val=10, max_val=40, row=3
        )

        # tRP
        self._add_field(
            form, "tRP", "tRP (cycles)",
            default=self.existing_data.get("tRP", 18) if self.existing_data else 18,
            min_val=10, max_val=40, row=4
        )

        # tRAS
        self._add_field(
            form, "tRAS", "tRAS (cycles)",
            default=self.existing_data.get("tRAS", 36) if self.existing_data else 36,
            min_val=20, max_val=80, row=5
        )

        # 预览
        self.preview_frame = ctk.CTkFrame(self, fg_color=Colors.CARD_BG, corner_radius=8)
        self.preview_frame.pack(fill="x", padx=30, pady=15)

        ctk.CTkLabel(
            self.preview_frame,
            text="预览",
            font=("Arial", 12, "bold")
        ).pack(anchor="w", padx=15, pady=(10, 5))

        self.preview_label = ctk.CTkLabel(
            self.preview_frame,
            text="",
            font=("Consolas", 14),
            text_color=Colors.HIGHLIGHT
        )
        self.preview_label.pack(anchor="w", padx=15, pady=(0, 10))

        # 风险指示
        self.risk_label = ctk.CTkLabel(
            self,
            text="",
            font=("Arial", 11),
            wraplength=400
        )
        self.risk_label.pack(pady=5)

        # 按钮
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=30, pady=20)

        ctk.CTkButton(
            btn_frame,
            text="取消",
            width=100,
            fg_color=Colors.SECONDARY,
            command=self.destroy
        ).pack(side="left")

        save_text = "创建" if self.is_create else "保存"
        self.save_btn = ctk.CTkButton(
            btn_frame,
            text=save_text,
            width=100,
            command=self._save
        )
        self.save_btn.pack(side="right")

    def _add_field(self, parent, key, label, default, min_val, max_val, row, is_float=False):
        """添加输入字段"""
        field_frame = ctk.CTkFrame(parent, fg_color="transparent")
        field_frame.grid(row=row, column=0, sticky="ew", pady=5)
        field_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            field_frame,
            text=label,
            width=140,
            anchor="w"
        ).grid(row=0, column=0)

        entry = ctk.CTkEntry(field_frame, width=100)
        entry.grid(row=0, column=1, padx=10)
        entry.insert(0, f"{default:.2f}" if is_float else str(default))
        entry.bind("<KeyRelease>", lambda e: self._update_preview())

        hint = f"({min_val}-{max_val})"
        ctk.CTkLabel(
            field_frame,
            text=hint,
            font=("Arial", 10),
            text_color=Colors.TEXT_SECONDARY
        ).grid(row=0, column=2)

        self.fields[key] = {
            "entry": entry,
            "min": min_val,
            "max": max_val,
            "is_float": is_float
        }

    def _get_values(self):
        """获取并验证所有字段值"""
        values = {}
        for key, field in self.fields.items():
            try:
                if field["is_float"]:
                    val = float(field["entry"].get())
                else:
                    val = int(field["entry"].get())
                val = max(field["min"], min(field["max"], val))
                values[key] = val
            except ValueError:
                return None
        return values

    def _update_preview(self):
        """更新预览和风险提示"""
        values = self._get_values()
        if values:
            timing_str = f"CL{values['CL']}-{values['tRCD']}-{values['tRP']}-{values['tRAS']}"
            preview = f"{values['frequency']} MT/s @ {values['voltage']:.2f}V ({timing_str})"
            self.preview_label.configure(text=preview)

            # 计算 tCK 并验证时序
            tck_ns = 2000 / values['frequency']
            taa_ns = values['CL'] * tck_ns
            risk, msg = validate_timing("tAA", taa_ns)

            if risk == RiskLevel.SAFE:
                self.risk_label.configure(
                    text="✓ 参数在合理范围内",
                    text_color=RISK_COLORS[risk]
                )
            else:
                self.risk_label.configure(
                    text=f"⚠️ {msg[:80]}...",
                    text_color=RISK_COLORS[risk]
                )

            self.save_btn.configure(state="normal")
        else:
            self.preview_label.configure(text="请输入有效数值")
            self.save_btn.configure(state="disabled")

    def _save(self):
        """保存"""
        values = self._get_values()
        if values and self.on_save:
            self.on_save(self.profile_num, values)
        self.destroy()
