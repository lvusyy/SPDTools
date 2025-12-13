"""
概览选项卡
展示内存的核心信息
"""

import customtkinter as ctk
from typing import Optional, Dict, Any

from ..widgets.info_card import InfoCard, LargeInfoCard, TimingCard
from ...core.model import SPDDataModel, DataChangeEvent
from ...core.parser import DDR4Parser
from ...utils.constants import Colors


class OverviewTab(ctk.CTkFrame):
    """概览选项卡"""

    def __init__(self, master, data_model: SPDDataModel, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self.data_model = data_model
        self.cards = {}
        self.display_mode = "spd"  # "spd" or "read"

        self.grid_columnconfigure((0, 1, 2), weight=1)
        self.grid_rowconfigure(3, weight=1)  # Changed from 2 to 3 for header row

        self._setup_ui()

        # 注册数据变更监听
        self.data_model.add_observer(self._on_data_changed)

    def _setup_ui(self):
        """设置UI"""
        # 第0行：模式切换按钮
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, columnspan=3, sticky="ew", padx=10, pady=(10, 0))

        self.mode_toggle = ctk.CTkSegmentedButton(
            header_frame,
            values=["SPD", "Read"],
            command=self._on_mode_change
        )
        self.mode_toggle.set("SPD")
        self.mode_toggle.pack(side="right")

        # 第一行：基本信息卡片
        self.cards["type"] = InfoCard(
            self,
            title="内存类型",
            value="-",
            subtitle="",
            width=200,
            height=90
        )
        self.cards["type"].grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        self.cards["capacity"] = InfoCard(
            self,
            title="容量",
            value="-",
            subtitle="",
            width=200,
            height=90
        )
        self.cards["capacity"].grid(row=1, column=1, padx=10, pady=10, sticky="nsew")

        self.cards["speed"] = InfoCard(
            self,
            title="速度等级",
            value="-",
            subtitle="",
            width=200,
            height=90
        )
        self.cards["speed"].grid(row=1, column=2, padx=10, pady=10, sticky="nsew")

        # 第二行：时序和制造商
        self.timing_card = TimingCard(self)
        self.timing_card.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")

        self.cards["manufacturer"] = InfoCard(
            self,
            title="制造商",
            value="-",
            subtitle="",
            width=200,
            height=120
        )
        self.cards["manufacturer"].grid(row=2, column=2, padx=10, pady=10, sticky="nsew")

        # 第三行：详细信息
        self.detail_card = LargeInfoCard(self, title="详细信息", width=400)
        self.detail_card.grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")

        self.xmp_card = LargeInfoCard(self, title="XMP 配置", width=300)
        self.xmp_card.grid(row=3, column=2, padx=10, pady=10, sticky="nsew")

    def _on_data_changed(self, event: DataChangeEvent):
        """数据变更回调"""
        self.refresh()

    def _on_mode_change(self, value: str):
        """模式切换回调"""
        self.display_mode = value.lower()
        self.refresh()

    def refresh(self):
        """刷新显示"""
        if not self.data_model.has_data:
            self._show_no_data()
            return

        # 解析数据 (使用当前显示模式)
        parser = DDR4Parser(self.data_model.data)
        info = parser.to_dict(mode=self.display_mode)

        if "error" in info:
            self._show_no_data()
            return

        # 更新卡片
        self.cards["type"].set_value(
            f"{info.get('memory_type', '-')}",
            info.get('module_type', '')
        )

        self.cards["capacity"].set_value(
            info.get('capacity', '-'),
            info.get('organization', '')
        )

        speed = info.get('speed_grade', 0)
        self.cards["speed"].set_value(
            f"{speed} MT/s" if speed else "-",
            f"DDR4-{speed}" if speed else ""
        )

        self.cards["manufacturer"].set_value(
            info.get('manufacturer', '-'),
            info.get('part_number', '')[:20] if info.get('part_number') else ''
        )

        # 更新时序
        timing_str = info.get('timing_string', 'CL--')
        timing_details = info.get('timings', {})
        self.timing_card.set_timings(timing_str, timing_details)

        # 更新详细信息
        self.detail_card.clear_items()
        self.detail_card.add_item("部件号", info.get('part_number', '-'))
        self.detail_card.add_item("序列号", info.get('serial_number', '-'))
        self.detail_card.add_item("生产日期", info.get('manufacturing_date', '-'))
        self.detail_card.add_item("电压", f"{info.get('voltage', 1.2):.1f}V")

        # DRAM 制造商（如果与模组制造商不同）
        dram_mfr = info.get('dram_manufacturer', {})
        if dram_mfr.get('name') != info.get('manufacturer'):
            self.detail_card.add_item("DRAM 制造商", dram_mfr.get('name', '-'))

        # Die 信息
        die_info = info.get('die_info', {})
        if self.display_mode == "read" and "die_info_inferred" in info:
            # Read 模式：显示推断的 Die 类型
            inferred = info["die_info_inferred"]
            die_desc = inferred.get("die_description", "-")
            if inferred.get("inferred"):
                die_desc += " (推断)"
            self.detail_card.add_item("Die 信息", die_desc)
        else:
            # SPD 模式：仅显示密度
            density = die_info.get('density_gb', 0)
            if density > 0:
                self.detail_card.add_item("Die 密度", f"{density} Gb")

        # Die 数量和封装类型
        die_count = die_info.get('die_count', 1)
        if die_count > 1:
            self.detail_card.add_item("Die 数量", str(die_count))
        package_type = die_info.get('package_type', '')
        if package_type and package_type != "Monolithic":
            self.detail_card.add_item("封装类型", package_type)

        # ECC 信息
        ecc_info = info.get('ecc_info', {})
        if ecc_info.get('has_ecc'):
            ecc_str = f"{ecc_info.get('primary_width')} bits + {ecc_info.get('extension_width')} bits ECC"
            self.detail_card.add_item("ECC", ecc_str)
        else:
            self.detail_card.add_item("总线宽度", f"{ecc_info.get('primary_width', '-')} bits")

        # Bank 配置
        bank_config = info.get('bank_config', {})
        bank_str = f"{bank_config.get('bank_groups', '-')} groups × {bank_config.get('banks_per_group', '-')} banks"
        self.detail_card.add_item("Bank 配置", bank_str)

        # 寻址信息
        addressing = info.get('addressing', {})
        self.detail_card.add_item("行/列地址", f"{addressing.get('row_bits', '-')} / {addressing.get('col_bits', '-')} bits")
        self.detail_card.add_item("页大小", addressing.get('page_size_str', '-'))

        # 温度传感器
        thermal = info.get('thermal_sensor', {})
        if thermal.get('present'):
            self.detail_card.add_item("温度传感器", "支持")

        # 更新 XMP 信息
        self.xmp_card.clear_items()
        xmp = info.get('xmp', {})
        if xmp.get('supported'):
            self.xmp_card.add_item("状态", f"支持 ({xmp.get('version', '-')})")
            for profile in xmp.get('profiles', []):
                self.xmp_card.add_item(
                    profile.get('name', 'Profile'),
                    f"{profile.get('frequency', '-')} MT/s"
                )
                self.xmp_card.add_item("  时序", profile.get('timings', '-'))
                self.xmp_card.add_item("  电压", f"{profile.get('voltage', 0):.2f}V")
        else:
            self.xmp_card.add_item("状态", "不支持")

        # 显示修改状态
        if self.data_model.is_modified:
            self._show_modified_indicator()

    def _show_no_data(self):
        """显示无数据状态"""
        for card in self.cards.values():
            card.set_value("-", "")

        self.timing_card.set_timings("CL--", {})
        self.detail_card.clear_items()
        self.detail_card.add_item("状态", "未加载数据")

        self.xmp_card.clear_items()
        self.xmp_card.add_item("状态", "-")

    def _show_modified_indicator(self):
        """显示修改指示"""
        count = self.data_model.modified_count
        if count > 0:
            # 可以在某个位置显示修改计数
            pass
