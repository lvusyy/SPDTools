"""
十六进制编辑器选项卡
"""

import customtkinter as ctk
from typing import Optional

from ..widgets.hex_view import HexView
from ...core.model import SPDDataModel, DataChangeEvent
from ...utils.constants import Colors


class HexEditorTab(ctk.CTkFrame):
    """十六进制编辑器选项卡"""

    def __init__(self, master, data_model: SPDDataModel, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self.data_model = data_model

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._setup_ui()
        self.data_model.add_observer(self._on_data_changed)

    def _setup_ui(self):
        """设置UI"""
        # 十六进制视图
        self.hex_view = HexView(
            self,
            data=self.data_model.data if self.data_model.has_data else None,
            editable=True,
            on_byte_changed=self._on_byte_changed,
            modified_bytes=self.data_model.modified_bytes
        )
        self.hex_view.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    def _on_byte_changed(self, offset: int, value: int):
        """字节变更回调"""
        self.data_model.set_byte(offset, value)

    def _on_data_changed(self, event: DataChangeEvent):
        """数据变更回调"""
        self.hex_view.set_data(
            self.data_model.data,
            self.data_model.modified_bytes
        )

    def highlight_byte(self, offset: int):
        """高亮指定字节"""
        self.hex_view.highlight_offset(offset)
