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

        self.grid_columnconfigure((0, 1, 2), weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._setup_ui()

        # 注册数据变更监听
        self.data_model.add_observer(self._on_data_changed)

    def _setup_ui(self):
        """设置UI"""
        # 第一行：基本信息卡片
        self.cards["type"] = InfoCard(
            self,
            title="内存类型",
            value="-",
            subtitle="",
            width=200,
            height=90
        )
        self.cards["type"].grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        self.cards["capacity"] = InfoCard(
            self,
            title="容量",
            value="-",
            subtitle="",
            width=200,
            height=90
        )
        self.cards["capacity"].grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        self.cards["speed"] = InfoCard(
            self,
            title="速度等级",
            value="-",
            subtitle="",
            width=200,
            height=90
        )
        self.cards["speed"].grid(row=0, column=2, padx=10, pady=10, sticky="nsew")

        # 第二行：时序和制造商
        self.timing_card = TimingCard(self)
        self.timing_card.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")

        self.cards["manufacturer"] = InfoCard(
            self,
            title="制造商",
            value="-",
            subtitle="",
            width=200,
            height=120
        )
        self.cards["manufacturer"].grid(row=1, column=2, padx=10, pady=10, sticky="nsew")

        # 第三行：详细信息
        self.detail_card = LargeInfoCard(self, title="详细信息", width=400)
        self.detail_card.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")

        self.xmp_card = LargeInfoCard(self, title="XMP 配置", width=300)
        self.xmp_card.grid(row=2, column=2, padx=10, pady=10, sticky="nsew")

    def _on_data_changed(self, event: DataChangeEvent):
        """数据变更回调"""
        self.refresh()

    def refresh(self):
        """刷新显示"""
        if not self.data_model.has_data:
            self._show_no_data()
            return

        # 解析数据
        parser = DDR4Parser(self.data_model.data)
        info = parser.to_dict()

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

        capacity_details = info.get('capacity_details', {})
        self.detail_card.add_item("密度/Die", f"{capacity_details.get('density_per_die_gb', '-')} Gb")
        self.detail_card.add_item("总线宽度", f"{capacity_details.get('bus_width', '-')} bit")

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
