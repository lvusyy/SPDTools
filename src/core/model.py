"""
SPD 数据模型
实现观察者模式，支持数据变更通知
"""

from typing import List, Optional, Callable, Set, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import os
from datetime import datetime

from ..utils.constants import SPD_SIZE


class DataChangeType(Enum):
    """数据变更类型"""
    BYTE_CHANGED = "byte_changed"      # 单字节修改
    RANGE_CHANGED = "range_changed"    # 范围修改
    DATA_LOADED = "data_loaded"        # 数据加载
    DATA_RESET = "data_reset"          # 数据重置


@dataclass
class DataChangeEvent:
    """数据变更事件"""
    change_type: DataChangeType
    offset: Optional[int] = None
    length: Optional[int] = None
    old_value: Optional[int] = None
    new_value: Optional[int] = None


class SPDDataModel:
    """
    SPD 数据模型

    实现观察者模式，当数据变更时通知所有注册的观察者
    """

    def __init__(self):
        self._data: List[int] = [0] * SPD_SIZE
        self._original_data: Optional[List[int]] = None
        self._observers: List[Callable[[DataChangeEvent], None]] = []
        self._modified_bytes: Set[int] = set()
        self._file_path: Optional[str] = None
        self._is_from_device: bool = False

    @property
    def data(self) -> List[int]:
        """获取数据副本"""
        return self._data.copy()

    @property
    def has_data(self) -> bool:
        """是否有有效数据"""
        return any(b != 0 for b in self._data)

    @property
    def is_modified(self) -> bool:
        """数据是否被修改"""
        return len(self._modified_bytes) > 0

    @property
    def modified_count(self) -> int:
        """获取修改的字节数"""
        return len(self._modified_bytes)

    @property
    def modified_bytes(self) -> Set[int]:
        """获取修改的字节索引集合"""
        return self._modified_bytes.copy()

    @property
    def file_path(self) -> Optional[str]:
        """获取文件路径"""
        return self._file_path

    @property
    def is_from_device(self) -> bool:
        """数据是否来自设备"""
        return self._is_from_device

    def add_observer(self, callback: Callable[[DataChangeEvent], None]) -> None:
        """
        添加观察者

        Args:
            callback: 数据变更时调用的回调函数
        """
        if callback not in self._observers:
            self._observers.append(callback)

    def remove_observer(self, callback: Callable[[DataChangeEvent], None]) -> None:
        """移除观察者"""
        if callback in self._observers:
            self._observers.remove(callback)

    def _notify_observers(self, event: DataChangeEvent) -> None:
        """通知所有观察者"""
        for callback in self._observers:
            try:
                callback(event)
            except Exception as e:
                print(f"Observer callback error: {e}")

    def load_from_list(
        self,
        data: List[int],
        is_from_device: bool = False,
        file_path: Optional[str] = None
    ) -> bool:
        """
        从列表加载数据

        Args:
            data: 512 字节数据列表
            is_from_device: 是否来自设备
            file_path: 文件路径（如果从文件加载）

        Returns:
            是否加载成功
        """
        if len(data) != SPD_SIZE:
            return False

        self._data = data.copy()
        self._original_data = data.copy()
        self._modified_bytes.clear()
        self._is_from_device = is_from_device
        self._file_path = file_path

        self._notify_observers(DataChangeEvent(
            change_type=DataChangeType.DATA_LOADED
        ))
        return True

    def load_from_file(self, path: str) -> bool:
        """
        从文件加载数据

        Args:
            path: 文件路径

        Returns:
            是否加载成功
        """
        try:
            with open(path, "rb") as f:
                content = f.read()
            if len(content) != SPD_SIZE:
                return False
            return self.load_from_list(list(content), is_from_device=False, file_path=path)
        except Exception:
            return False

    def save_to_file(self, path: str) -> bool:
        """
        保存数据到文件

        Args:
            path: 文件路径

        Returns:
            是否保存成功
        """
        try:
            with open(path, "wb") as f:
                f.write(bytearray(self._data))
            self._file_path = path
            return True
        except Exception:
            return False

    def get_byte(self, offset: int) -> int:
        """获取指定偏移的字节值"""
        if 0 <= offset < SPD_SIZE:
            return self._data[offset]
        return 0

    def set_byte(self, offset: int, value: int) -> bool:
        """
        设置指定偏移的字节值

        Args:
            offset: 字节偏移
            value: 新值 (0-255)

        Returns:
            是否设置成功
        """
        if not (0 <= offset < SPD_SIZE) or not (0 <= value <= 255):
            return False

        old_value = self._data[offset]
        if old_value == value:
            return True

        self._data[offset] = value

        # 更新修改标记
        if self._original_data:
            if self._data[offset] != self._original_data[offset]:
                self._modified_bytes.add(offset)
            elif offset in self._modified_bytes:
                self._modified_bytes.discard(offset)

        self._notify_observers(DataChangeEvent(
            change_type=DataChangeType.BYTE_CHANGED,
            offset=offset,
            old_value=old_value,
            new_value=value
        ))
        return True

    def set_bytes(self, offset: int, values: List[int]) -> bool:
        """
        设置一段连续的字节值

        Args:
            offset: 起始偏移
            values: 字节值列表

        Returns:
            是否设置成功
        """
        if offset < 0 or offset + len(values) > SPD_SIZE:
            return False

        for i, value in enumerate(values):
            if not (0 <= value <= 255):
                return False

        # 批量更新
        for i, value in enumerate(values):
            pos = offset + i
            old_value = self._data[pos]
            self._data[pos] = value

            if self._original_data:
                if self._data[pos] != self._original_data[pos]:
                    self._modified_bytes.add(pos)
                elif pos in self._modified_bytes:
                    self._modified_bytes.discard(pos)

        self._notify_observers(DataChangeEvent(
            change_type=DataChangeType.RANGE_CHANGED,
            offset=offset,
            length=len(values)
        ))
        return True

    def get_range(self, offset: int, length: int) -> List[int]:
        """获取一段连续的字节"""
        if offset < 0 or offset + length > SPD_SIZE:
            return []
        return self._data[offset:offset + length]

    def is_byte_modified(self, offset: int) -> bool:
        """检查指定字节是否被修改"""
        return offset in self._modified_bytes

    def get_original_byte(self, offset: int) -> Optional[int]:
        """获取原始字节值"""
        if self._original_data and 0 <= offset < SPD_SIZE:
            return self._original_data[offset]
        return None

    def reset_to_original(self) -> bool:
        """重置为原始数据"""
        if not self._original_data:
            return False

        self._data = self._original_data.copy()
        self._modified_bytes.clear()

        self._notify_observers(DataChangeEvent(
            change_type=DataChangeType.DATA_RESET
        ))
        return True

    def reset_byte(self, offset: int) -> bool:
        """重置单个字节为原始值"""
        if not self._original_data or not (0 <= offset < SPD_SIZE):
            return False

        return self.set_byte(offset, self._original_data[offset])

    def get_modifications(self) -> Dict[int, tuple]:
        """
        获取所有修改

        Returns:
            字典，键为偏移，值为 (原值, 新值) 元组
        """
        if not self._original_data:
            return {}

        modifications = {}
        for offset in self._modified_bytes:
            modifications[offset] = (
                self._original_data[offset],
                self._data[offset]
            )
        return modifications

    def clear(self) -> None:
        """清空数据"""
        self._data = [0] * SPD_SIZE
        self._original_data = None
        self._modified_bytes.clear()
        self._file_path = None
        self._is_from_device = False

        self._notify_observers(DataChangeEvent(
            change_type=DataChangeType.DATA_RESET
        ))

    def export_to_json(self) -> Dict[str, Any]:
        """导出为 JSON 格式"""
        from .parser import DDR4Parser
        parser = DDR4Parser(self._data)

        return {
            "export_time": datetime.now().isoformat(),
            "source": "device" if self._is_from_device else self._file_path or "unknown",
            "raw_data": self._data,
            "parsed_info": parser.to_dict(),
            "modifications": {
                str(k): {"original": v[0], "current": v[1]}
                for k, v in self.get_modifications().items()
            }
        }

    def export_to_text(self) -> str:
        """导出为文本报告"""
        from .parser import DDR4Parser
        parser = DDR4Parser(self._data)
        info = parser.to_dict()

        lines = [
            "=" * 50,
            "SPD 数据报告",
            "=" * 50,
            f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"数据来源: {'设备读取' if self._is_from_device else self._file_path or '未知'}",
            "",
            "-" * 50,
            "基本信息",
            "-" * 50,
            f"内存类型: {info.get('memory_type', '未知')}",
            f"模组类型: {info.get('module_type', '未知')}",
            f"容量: {info.get('capacity', '未知')}",
            f"速度等级: {info.get('speed_grade', '未知')} MT/s",
            "",
            "-" * 50,
            "制造商信息",
            "-" * 50,
            f"制造商: {info.get('manufacturer', '未知')}",
            f"部件号: {info.get('part_number', '未知')}",
            f"序列号: {info.get('serial_number', '未知')}",
            f"生产日期: {info.get('manufacturing_date', '未知')}",
            "",
            "-" * 50,
            "时序参数",
            "-" * 50,
        ]

        timings = info.get('timings', {})
        for name, value in timings.items():
            lines.append(f"{name}: {value}")

        if self._modified_bytes:
            lines.extend([
                "",
                "-" * 50,
                f"修改记录 ({len(self._modified_bytes)} 字节)",
                "-" * 50,
            ])
            for offset, (old, new) in sorted(self.get_modifications().items()):
                lines.append(f"Offset 0x{offset:03X}: 0x{old:02X} -> 0x{new:02X}")

        lines.append("")
        lines.append("=" * 50)

        return "\n".join(lines)

    def compare_with(self, other_data: List[int]) -> Dict[int, tuple]:
        """
        与其他数据对比

        Args:
            other_data: 要对比的数据

        Returns:
            差异字典，键为偏移，值为 (本数据值, 对比数据值)
        """
        if len(other_data) != SPD_SIZE:
            return {}

        differences = {}
        for i in range(SPD_SIZE):
            if self._data[i] != other_data[i]:
                differences[i] = (self._data[i], other_data[i])
        return differences
