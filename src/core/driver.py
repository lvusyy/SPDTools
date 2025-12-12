"""
SPD 硬件驱动层
负责与 HID 设备通信，读写 SPD 数据
"""

import hid
import time
from typing import Optional, Callable, List

from ..utils.constants import DEFAULT_VID, DEFAULT_PID, SPD_SIZE, SPD_PAGE_SIZE


class SPDDriver:
    """SPD 读写器硬件驱动"""

    def __init__(self, vid: int = DEFAULT_VID, pid: int = DEFAULT_PID):
        self.vid = vid
        self.pid = pid
        self.device: Optional[hid.device] = None
        self.stop_flag = False

    def connect(self) -> bool:
        """连接到 HID 设备"""
        try:
            self.device = hid.device()
            self.device.open(self.vid, self.pid)
            return True
        except Exception:
            self.device = None
            return False

    def disconnect(self) -> None:
        """断开设备连接"""
        if self.device:
            self.device.close()
            self.device = None

    def is_connected(self) -> bool:
        """检查设备是否已连接"""
        return self.device is not None

    def send_cmd(self, cmd_str: str, delay: float = 0.02) -> Optional[str]:
        """
        发送命令到设备并读取响应

        Args:
            cmd_str: 命令字符串
            delay: 等待响应的延时（秒）

        Returns:
            响应字符串，失败返回 None
        """
        if not self.device:
            return None

        # 构造数据包: ReportID(0) + 64 bytes data
        data = [0x00] * 65
        for i, char in enumerate(cmd_str):
            if i + 1 < len(data):
                data[i + 1] = ord(char)

        try:
            self.device.write(data)
            time.sleep(delay)
            response = self.device.read(64)
            return "".join([chr(x) for x in response if 32 <= x <= 126])
        except Exception as e:
            print(f"IO Error: {e}")
            return None

    def read_spd(
        self,
        progress_callback: Optional[Callable[[float], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Optional[List[int]]:
        """
        读取完整的 512 字节 SPD 数据

        Args:
            progress_callback: 进度回调函数，参数为 0-1 的进度值
            log_callback: 日志回调函数

        Returns:
            512 字节的数据列表，失败返回 None
        """
        self.stop_flag = False
        full_data = [0] * SPD_SIZE

        # 1. 激活与初始化
        self.send_cmd("BT-VER0010")
        time.sleep(0.1)

        # 2. 读取 Page 0 (0-255)
        if log_callback:
            log_callback("正在读取 Page 0...")
        self.send_cmd("BT-I2C2WR360001")
        time.sleep(0.2)

        for offset in range(0, SPD_PAGE_SIZE, 8):
            if self.stop_flag:
                return None
            block = self._read_block(0x50, offset)
            for i, b in enumerate(block):
                full_data[offset + i] = b
            if progress_callback:
                progress_callback((offset + 8) / SPD_SIZE)

        # 3. 读取 Page 1 (256-511)
        if log_callback:
            log_callback("正在读取 Page 1...")
        self.send_cmd("BT-I2C2WR370001")
        time.sleep(0.4)

        for offset in range(0, SPD_PAGE_SIZE, 8):
            if self.stop_flag:
                return None
            block = self._read_block(0x50, offset)
            for i, b in enumerate(block):
                full_data[SPD_PAGE_SIZE + offset + i] = b
            if progress_callback:
                progress_callback((SPD_PAGE_SIZE + offset + 8) / SPD_SIZE)

        return full_data

    def _read_block(self, addr: int, offset: int) -> List[int]:
        """
        读取 8 字节数据块

        Args:
            addr: I2C 地址
            offset: 页内偏移

        Returns:
            8 字节数据列表
        """
        cmd = f"BT-I2C2RD{addr:02X}{offset:02X}08"
        for _ in range(3):  # 重试 3 次
            resp = self.send_cmd(cmd)
            if resp and resp.startswith(":"):
                try:
                    parts = resp[1:].strip().split()
                    hex_parts = [p for p in parts if len(p) == 2][:8]
                    if len(hex_parts) == 8:
                        return [int(x, 16) for x in hex_parts]
                except Exception:
                    pass
            time.sleep(0.05)
        return [0] * 8

    def write_spd(
        self,
        data: List[int],
        progress_callback: Optional[Callable[[float], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> bool:
        """
        写入 SPD 数据到内存条

        Args:
            data: 512 字节数据列表
            progress_callback: 进度回调函数
            log_callback: 日志回调函数

        Returns:
            是否写入成功
        """
        self.stop_flag = False

        if len(data) != SPD_SIZE:
            if log_callback:
                log_callback(f"错误: 数据长度必须是 {SPD_SIZE} 字节")
            return False

        # 1. 激活
        self.send_cmd("BT-VER0010")
        time.sleep(0.1)

        # 2. 写入 Page 0 (0-255)
        if log_callback:
            log_callback("正在写入 Page 0...")
        self.send_cmd("BT-I2C2WR360001")
        time.sleep(0.2)

        for offset in range(0, SPD_PAGE_SIZE, 8):
            if self.stop_flag:
                return False
            chunk = data[offset:offset + 8]
            if not self._write_block(0x50, offset, chunk):
                if log_callback:
                    log_callback(f"写入失败: Offset {hex(offset)}")
                return False
            if progress_callback:
                progress_callback((offset + 8) / SPD_SIZE)

        # 3. 写入 Page 1 (256-511)
        if log_callback:
            log_callback("正在写入 Page 1...")
        self.send_cmd("BT-I2C2WR370001")
        time.sleep(0.4)

        for offset in range(0, SPD_PAGE_SIZE, 8):
            if self.stop_flag:
                return False
            chunk = data[SPD_PAGE_SIZE + offset:SPD_PAGE_SIZE + offset + 8]
            if not self._write_block(0x50, offset, chunk):
                if log_callback:
                    log_callback(f"写入失败: Offset {hex(SPD_PAGE_SIZE + offset)}")
                return False
            if progress_callback:
                progress_callback((SPD_PAGE_SIZE + offset + 8) / SPD_SIZE)

        if log_callback:
            log_callback("写入完成，请重启电脑！")
        return True

    def _write_block(self, addr: int, offset: int, data_bytes: List[int]) -> bool:
        """
        写入 8 字节数据块

        Args:
            addr: I2C 地址
            offset: 页内偏移
            data_bytes: 8 字节数据

        Returns:
            是否写入成功
        """
        data_hex = "".join(f"{b:02X}" for b in data_bytes)
        cmd = f"BT-I2C2WR{addr:02X}{offset:02X}08{data_hex}"
        self.send_cmd(cmd, delay=0.1)
        return True

    def stop(self) -> None:
        """停止当前操作"""
        self.stop_flag = True

    def verify_spd(
        self,
        data: List[int],
        log_callback: Optional[Callable[[str], None]] = None
    ) -> bool:
        """
        验证写入的数据（回读对比）

        Args:
            data: 预期数据
            log_callback: 日志回调

        Returns:
            验证是否通过
        """
        if log_callback:
            log_callback("正在验证数据...")

        read_data = self.read_spd(log_callback=log_callback)
        if not read_data:
            if log_callback:
                log_callback("验证失败: 无法读取数据")
            return False

        mismatches = []
        for i, (expected, actual) in enumerate(zip(data, read_data)):
            if expected != actual:
                mismatches.append((i, expected, actual))

        if mismatches:
            if log_callback:
                log_callback(f"验证失败: {len(mismatches)} 字节不匹配")
                for offset, expected, actual in mismatches[:5]:
                    log_callback(f"  Offset {offset:03X}: 预期 {expected:02X}, 实际 {actual:02X}")
                if len(mismatches) > 5:
                    log_callback(f"  ... 还有 {len(mismatches) - 5} 处不匹配")
            return False

        if log_callback:
            log_callback("验证通过！")
        return True
