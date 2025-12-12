"""
详细参数选项卡
展示并允许编辑所有 SPD 参数
"""

import customtkinter as ctk
from typing import Optional, Dict, Any

from ..widgets.editable_field import EditableField
from ...core.model import SPDDataModel, DataChangeEvent
from ...core.parser import DDR4Parser
from ...core.parser.manufacturers import COMMON_MANUFACTURERS, get_manufacturer_id
from ...utils.constants import Colors, SPD_BYTES, MODULE_TYPES


class DetailsTab(ctk.CTkFrame):
    """详细参数选项卡"""

    def __init__(self, master, data_model: SPDDataModel, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self.data_model = data_model
        self.fields = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._setup_ui()
        self.data_model.add_observer(self._on_data_changed)

    def _setup_ui(self):
        """设置UI"""
        # 可滚动区域
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.scroll_frame.grid_columnconfigure(0, weight=1)

        # 分组：基本信息
        self._create_section("基本信息", [
            ("内存类型", "memory_type", "text", False),
            ("模组类型", "module_type", "select", True, list(MODULE_TYPES.values())),
            ("容量", "capacity", "text", False),
            ("组织结构", "organization", "text", False),
            ("总线宽度", "bus_width", "text", False),
        ])

        # 分组：速度配置
        self._create_section("速度配置", [
            ("速度等级", "speed_grade", "number", True, 1600, 5000),
            ("电压", "voltage", "text", False),
        ])

        # 分组：制造商信息
        self._create_section("制造商信息", [
            ("制造商", "manufacturer", "select", True, COMMON_MANUFACTURERS),
            ("部件号", "part_number", "text", True),
            ("序列号", "serial_number", "hex", True),
            ("生产日期", "manufacturing_date", "text", True),
        ])

        # 分组：SPD 元数据
        self._create_section("SPD 元数据", [
            ("SPD 字节使用", "spd_bytes_used", "text", False),
            ("SPD 修订版", "spd_revision", "text", False),
        ])

    def _create_section(self, title: str, fields: list):
        """创建一个参数分组"""
        # 分组标题
        section_frame = ctk.CTkFrame(self.scroll_frame, fg_color=Colors.CARD_BG, corner_radius=10)
        section_frame.pack(fill="x", pady=(0, 15))
        section_frame.grid_columnconfigure(0, weight=1)

        # 标题
        title_label = ctk.CTkLabel(
            section_frame,
            text=title,
            font=("Arial", 14, "bold"),
            text_color=Colors.TEXT
        )
        title_label.grid(row=0, column=0, sticky="w", padx=15, pady=(12, 8))

        # 分隔线
        separator = ctk.CTkFrame(section_frame, height=1, fg_color=Colors.SECONDARY)
        separator.grid(row=1, column=0, sticky="ew", padx=15)

        # 字段
        for i, field_config in enumerate(fields):
            name = field_config[0]
            key = field_config[1]
            field_type = field_config[2]
            editable = field_config[3] if len(field_config) > 3 else False

            options = None
            min_val = None
            max_val = None

            if field_type == "select" and len(field_config) > 4:
                options = field_config[4]
            elif field_type == "number" and len(field_config) > 5:
                min_val = field_config[4]
                max_val = field_config[5]

            field = EditableField(
                section_frame,
                label=name,
                value="-",
                field_type=field_type,
                options=options,
                min_value=min_val,
                max_value=max_val,
                editable=editable,
                on_change=lambda n, v, k=key: self._on_field_changed(k, v)
            )
            field.grid(row=i + 2, column=0, sticky="ew", padx=15, pady=5)
            self.fields[key] = field

        # 底部间距
        ctk.CTkFrame(section_frame, height=10, fg_color="transparent").grid(
            row=len(fields) + 2, column=0
        )

    def _on_data_changed(self, event: DataChangeEvent):
        """数据变更回调"""
        self.refresh()

    def _on_field_changed(self, key: str, value: str):
        """字段变更回调"""
        if not self.data_model.has_data:
            return

        print(f"[DEBUG] Field changed: key={key}, value={value}")

        # 根据字段类型更新 SPD 数据
        if key == "manufacturer":
            # 更新制造商 ID
            first_byte, second_byte = get_manufacturer_id(value)
            print(f"[DEBUG] Manufacturer ID: first_byte=0x{first_byte:02X}, second_byte=0x{second_byte:02X}")
            # 移除不必要的条件检查，始终更新
            self.data_model.set_byte(SPD_BYTES.MANUFACTURER_ID_FIRST, first_byte)
            self.data_model.set_byte(SPD_BYTES.MANUFACTURER_ID_SECOND, second_byte)
            print(f"[DEBUG] Updated manufacturer bytes at {SPD_BYTES.MANUFACTURER_ID_FIRST} and {SPD_BYTES.MANUFACTURER_ID_SECOND}")

        elif key == "part_number":
            # 更新部件号 (20 字符，右侧填充空格)
            part_number = value.ljust(20)[:20]
            for i, char in enumerate(part_number):
                offset = SPD_BYTES.PART_NUMBER_START + i
                self.data_model.set_byte(offset, ord(char))

        elif key == "serial_number":
            # 更新序列号 (4 字节十六进制)
            try:
                hex_str = value.replace("0x", "").replace("0X", "").replace(" ", "")
                if len(hex_str) <= 8:
                    hex_str = hex_str.zfill(8)
                    for i in range(4):
                        byte_val = int(hex_str[i*2:(i+1)*2], 16)
                        self.data_model.set_byte(SPD_BYTES.SERIAL_NUMBER_1 + i, byte_val)
            except ValueError:
                pass

        elif key == "manufacturing_date":
            # 更新生产日期 (格式: YYYY-WXX 或 WXX/YYYY)
            try:
                # 尝试解析各种格式
                value = value.strip()
                year = None
                week = None

                if "/" in value:
                    # 格式: W26/2023 或 26/2023
                    parts = value.split("/")
                    week_part = parts[0].replace("W", "").replace("w", "")
                    week = int(week_part)
                    year = int(parts[1]) % 100  # 取后两位
                elif "-W" in value.upper():
                    # 格式: 2023-W26
                    parts = value.upper().split("-W")
                    year = int(parts[0]) % 100
                    week = int(parts[1])
                elif len(value) == 4 and value.isdigit():
                    # 只有年份
                    year = int(value) % 100
                    week = 1

                if year is not None:
                    self.data_model.set_byte(SPD_BYTES.MANUFACTURING_YEAR, year)
                if week is not None:
                    self.data_model.set_byte(SPD_BYTES.MANUFACTURING_WEEK, week)
            except (ValueError, IndexError):
                pass

        elif key == "module_type":
            # 更新模组类型
            for type_code, type_name in MODULE_TYPES.items():
                if type_name == value:
                    self.data_model.set_byte(SPD_BYTES.MODULE_TYPE, type_code)
                    break

        elif key == "speed_grade":
            # 更新速度等级 (通过修改 tCK_min)
            # 速度等级 = 2000000 / tCK_min (ps)
            # tCK_min = 2000000 / speed_grade
            try:
                speed = int(value)
                if 1600 <= speed <= 5000:
                    # tCK_min in ps, MTB = 125ps
                    tck_ps = 2000000 / speed
                    tck_mtb = int(tck_ps / 125)
                    self.data_model.set_byte(SPD_BYTES.TCK_MIN, tck_mtb)
            except ValueError:
                pass

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

        # 更新字段值
        field_mapping = {
            "memory_type": info.get("memory_type", "-"),
            "module_type": info.get("module_type", "-"),
            "capacity": info.get("capacity", "-"),
            "organization": info.get("organization", "-"),
            "bus_width": f"{info.get('capacity_details', {}).get('bus_width', '-')} bit",
            "speed_grade": str(info.get("speed_grade", "-")),
            "voltage": f"{info.get('voltage', 1.2):.1f}V",
            "manufacturer": info.get("manufacturer", "-"),
            "part_number": info.get("part_number", "-"),
            "serial_number": info.get("serial_number", "-"),
            "manufacturing_date": info.get("manufacturing_date", "-"),
            "spd_bytes_used": f"{self.data_model.data[0]} bytes" if self.data_model.has_data else "-",
            "spd_revision": f"{self.data_model.data[1] >> 4}.{self.data_model.data[1] & 0x0F}" if self.data_model.has_data else "-",
        }

        for key, value in field_mapping.items():
            if key in self.fields:
                self.fields[key].set_value(str(value))

    def _show_no_data(self):
        """显示无数据状态"""
        for field in self.fields.values():
            field.set_value("-")
