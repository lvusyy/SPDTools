"""
DDR4 SPD 解析器
根据 JEDEC 标准解析 DDR4 内存 SPD 数据
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .manufacturers import get_manufacturer_name
from ...utils.constants import (
    SPD_SIZE, SPD_BYTES, DDR4_TYPE, MODULE_TYPES,
    DENSITY_MAP, DEVICE_WIDTH, ROW_BITS, COL_BITS,
    MTB, FTB, SPEED_GRADES, XMP_MAGIC
)


@dataclass
class TimingInfo:
    """时序信息"""
    tCK: float = 0      # 时钟周期 (ns)
    tAA: float = 0      # CAS Latency (ns)
    tRCD: float = 0     # RAS to CAS Delay (ns)
    tRP: float = 0      # Row Precharge (ns)
    tRAS: float = 0     # Active to Precharge (ns)
    tRC: float = 0      # Active to Active/Refresh (ns)
    tRFC1: float = 0    # Refresh Recovery (ns)
    tFAW: float = 0     # Four Activate Window (ns)
    tRRD_S: float = 0   # Activate to Activate (different bank group)
    tRRD_L: float = 0   # Activate to Activate (same bank group)
    tCCD_L: float = 0   # CAS to CAS (same bank group)
    CL: int = 0         # CAS Latency (cycles)


@dataclass
class XMPProfile:
    """XMP 配置文件"""
    enabled: bool = False
    voltage: float = 0
    frequency: int = 0
    tCK: float = 0
    CL: int = 0
    tRCD: int = 0
    tRP: int = 0
    tRAS: int = 0


class DDR4Parser:
    """DDR4 SPD 数据解析器"""

    def __init__(self, data: List[int]):
        """
        初始化解析器

        Args:
            data: 512 字节的 SPD 数据
        """
        self.data = data if len(data) >= SPD_SIZE else data + [0] * (SPD_SIZE - len(data))

    def is_valid(self) -> bool:
        """检查数据是否有效"""
        return len(self.data) >= 256 and self.data[SPD_BYTES.DRAM_TYPE] == DDR4_TYPE

    def parse_memory_type(self) -> str:
        """解析内存类型"""
        dram_type = self.data[SPD_BYTES.DRAM_TYPE]
        if dram_type == DDR4_TYPE:
            return "DDR4"
        elif dram_type == 0x0E:
            return "DDR5"
        elif dram_type == 0x0B:
            return "DDR3"
        return f"Unknown (0x{dram_type:02X})"

    def parse_module_type(self) -> str:
        """解析模组类型"""
        module_byte = self.data[SPD_BYTES.MODULE_TYPE] & 0x0F
        return MODULE_TYPES.get(module_byte, f"Unknown (0x{module_byte:02X})")

    def parse_capacity(self) -> Dict[str, Any]:
        """
        解析容量信息

        Returns:
            包含容量相关信息的字典
        """
        density_byte = self.data[SPD_BYTES.DENSITY_BANKS]
        addressing_byte = self.data[SPD_BYTES.ADDRESSING]
        org_byte = self.data[SPD_BYTES.MODULE_ORG]
        width_byte = self.data[SPD_BYTES.BUS_WIDTH]

        # 密度 (per die)
        density_code = density_byte & 0x0F
        density_gb = DENSITY_MAP.get(density_code, 0)

        # Bank 组数
        bank_groups = 4 if ((density_byte >> 6) & 0x03) == 0 else 2

        # 行/列地址位数
        row_code = (addressing_byte >> 3) & 0x07
        col_code = addressing_byte & 0x07
        row_bits = ROW_BITS.get(row_code, 0)
        col_bits = COL_BITS.get(col_code, 0)

        # 设备宽度
        device_width_code = (org_byte >> 0) & 0x07
        device_width = DEVICE_WIDTH.get(device_width_code, 8)

        # Rank 数
        ranks = ((org_byte >> 3) & 0x07) + 1

        # 总线宽度
        bus_width_code = width_byte & 0x07
        bus_width = 8 * (1 << bus_width_code)  # 8, 16, 32, 64

        # 计算总容量 (GB)
        # 容量 = 密度 * (64 / 设备宽度) * Rank数 / 8
        if device_width > 0:
            capacity_gb = density_gb * (64 / device_width) * ranks / 8
        else:
            capacity_gb = 0

        return {
            "density_per_die_gb": density_gb,
            "bank_groups": bank_groups,
            "row_bits": row_bits,
            "col_bits": col_bits,
            "device_width": device_width,
            "ranks": ranks,
            "bus_width": bus_width,
            "total_capacity_gb": capacity_gb,
            "capacity_str": self._format_capacity(capacity_gb),
            "organization": f"{ranks}Rx{device_width}"
        }

    def _format_capacity(self, capacity_gb: float) -> str:
        """格式化容量显示"""
        if capacity_gb >= 1:
            if capacity_gb == int(capacity_gb):
                return f"{int(capacity_gb)} GB"
            return f"{capacity_gb:.1f} GB"
        else:
            mb = int(capacity_gb * 1024)
            return f"{mb} MB"

    def parse_voltage(self) -> Dict[str, Any]:
        """解析电压信息"""
        voltage_byte = self.data[SPD_BYTES.VOLTAGE]

        # DDR4 标准电压
        voltages = {
            "nominal": 1.2,
            "endurant": (voltage_byte & 0x02) != 0,  # 1.2V operable
            "1.2v_operable": (voltage_byte & 0x02) != 0,
        }

        return voltages

    def parse_timings(self) -> TimingInfo:
        """解析时序参数"""
        timing = TimingInfo()

        # tCK (时钟周期)
        tck_mtb = self.data[SPD_BYTES.TCK_MIN]
        tck_ftb = self._signed_byte(self.data[SPD_BYTES.TCK_MIN_FTB])
        timing.tCK = (tck_mtb * MTB + tck_ftb * FTB) / 1000  # 转换为 ns

        # tAA (CAS Latency Time)
        taa_mtb = self.data[SPD_BYTES.TAA_MIN]
        taa_ftb = self._signed_byte(self.data[SPD_BYTES.TAA_MIN_FTB])
        timing.tAA = (taa_mtb * MTB + taa_ftb * FTB) / 1000

        # tRCD
        trcd_mtb = self.data[SPD_BYTES.TRCD_MIN]
        trcd_ftb = self._signed_byte(self.data[SPD_BYTES.TRCD_MIN_FTB])
        timing.tRCD = (trcd_mtb * MTB + trcd_ftb * FTB) / 1000

        # tRP
        trp_mtb = self.data[SPD_BYTES.TRP_MIN]
        trp_ftb = self._signed_byte(self.data[SPD_BYTES.TRP_MIN_FTB])
        timing.tRP = (trp_mtb * MTB + trp_ftb * FTB) / 1000

        # tRAS
        tras_high = (self.data[SPD_BYTES.TRAS_TRC_HIGH] & 0x0F) << 8
        tras_low = self.data[SPD_BYTES.TRAS_MIN_LOW]
        timing.tRAS = (tras_high + tras_low) * MTB / 1000

        # tRC
        trc_high = (self.data[SPD_BYTES.TRAS_TRC_HIGH] >> 4) << 8
        trc_low = self.data[SPD_BYTES.TRC_MIN_LOW]
        trc_ftb = self._signed_byte(self.data[SPD_BYTES.TRC_MIN_FTB])
        timing.tRC = ((trc_high + trc_low) * MTB + trc_ftb * FTB) / 1000

        # tRFC1
        trfc1 = (self.data[SPD_BYTES.TRFC1_HIGH] << 8) + self.data[SPD_BYTES.TRFC1_LOW]
        timing.tRFC1 = trfc1 * MTB / 1000

        # tFAW
        tfaw_high = (self.data[SPD_BYTES.TFAW_HIGH] & 0x0F) << 8
        tfaw_low = self.data[SPD_BYTES.TFAW_LOW]
        timing.tFAW = (tfaw_high + tfaw_low) * MTB / 1000

        # tRRD_S
        timing.tRRD_S = self.data[SPD_BYTES.TRRD_S_MIN] * MTB / 1000

        # tRRD_L
        timing.tRRD_L = self.data[SPD_BYTES.TRRD_L_MIN] * MTB / 1000

        # tCCD_L
        timing.tCCD_L = self.data[SPD_BYTES.TCCD_L_MIN] * MTB / 1000

        # 计算 CL (cycles)
        if timing.tCK > 0:
            timing.CL = round(timing.tAA / timing.tCK)

        return timing

    def _signed_byte(self, value: int) -> int:
        """将无符号字节转换为有符号"""
        return value if value < 128 else value - 256

    def parse_speed_grade(self) -> int:
        """解析速度等级 (MT/s)"""
        tck_mtb = self.data[SPD_BYTES.TCK_MIN]
        tck_ftb = self._signed_byte(self.data[SPD_BYTES.TCK_MIN_FTB])
        tck_ps = tck_mtb * MTB + tck_ftb * FTB

        if tck_ps <= 0:
            return 0

        for (min_ps, max_ps), speed in SPEED_GRADES.items():
            if min_ps <= tck_ps < max_ps:
                return speed

        # 计算精确频率
        return int(2000000 / tck_ps) if tck_ps > 0 else 0

    def parse_cas_latencies(self) -> List[int]:
        """解析支持的 CAS 延迟"""
        cl_bytes = [
            self.data[SPD_BYTES.CAS_LATENCIES_1],
            self.data[SPD_BYTES.CAS_LATENCIES_2],
            self.data[SPD_BYTES.CAS_LATENCIES_3],
            self.data[SPD_BYTES.CAS_LATENCIES_4],
        ]

        supported_cl = []
        for byte_idx, byte_val in enumerate(cl_bytes):
            for bit in range(8):
                if byte_val & (1 << bit):
                    cl = 7 + byte_idx * 8 + bit  # CL7 起始
                    supported_cl.append(cl)

        return supported_cl

    def parse_manufacturer(self) -> Dict[str, str]:
        """解析制造商信息"""
        first_byte = self.data[SPD_BYTES.MANUFACTURER_ID_FIRST]
        second_byte = self.data[SPD_BYTES.MANUFACTURER_ID_SECOND]

        manufacturer = get_manufacturer_name(first_byte, second_byte)

        return {
            "name": manufacturer,
            "id_bytes": f"0x{first_byte:02X}{second_byte:02X}",
        }

    def parse_part_number(self) -> str:
        """解析部件号"""
        part_bytes = self.data[SPD_BYTES.PART_NUMBER_START:SPD_BYTES.PART_NUMBER_END + 1]
        part_number = "".join(chr(b) if 32 <= b < 127 else "" for b in part_bytes)
        return part_number.strip()

    def parse_serial_number(self) -> str:
        """解析序列号"""
        sn_bytes = self.data[SPD_BYTES.SERIAL_NUMBER_1:SPD_BYTES.SERIAL_NUMBER_4 + 1]
        return "".join(f"{b:02X}" for b in sn_bytes)

    def parse_manufacturing_date(self) -> str:
        """解析生产日期"""
        year = self.data[SPD_BYTES.MANUFACTURING_YEAR]
        week = self.data[SPD_BYTES.MANUFACTURING_WEEK]

        if year == 0 or year == 0xFF:
            return "Unknown"

        # BCD 编码
        year_str = f"20{(year >> 4) & 0x0F}{year & 0x0F}"
        week_str = f"{(week >> 4) & 0x0F}{week & 0x0F}"

        return f"{year_str} Week {week_str}"

    def parse_xmp(self) -> Dict[str, Any]:
        """解析 XMP 配置"""
        result = {
            "supported": False,
            "version": None,
            "profiles": []
        }

        if len(self.data) < 440:
            return result

        xmp_header = self.data[SPD_BYTES.XMP_HEADER]

        if xmp_header == XMP_MAGIC:
            result["supported"] = True
            result["version"] = "2.0"

            # 解析 Profile 1
            profile1 = self._parse_xmp_profile(SPD_BYTES.XMP_PROFILE1_START)
            if profile1.enabled:
                result["profiles"].append({
                    "name": "Profile 1",
                    "voltage": profile1.voltage,
                    "frequency": profile1.frequency,
                    "timings": f"CL{profile1.CL}-{profile1.tRCD}-{profile1.tRP}-{profile1.tRAS}"
                })

            # 解析 Profile 2
            if len(self.data) >= 487:
                profile2 = self._parse_xmp_profile(SPD_BYTES.XMP_PROFILE2_START)
                if profile2.enabled:
                    result["profiles"].append({
                        "name": "Profile 2",
                        "voltage": profile2.voltage,
                        "frequency": profile2.frequency,
                        "timings": f"CL{profile2.CL}-{profile2.tRCD}-{profile2.tRP}-{profile2.tRAS}"
                    })

        return result

    def _parse_xmp_profile(self, start_offset: int) -> XMPProfile:
        """解析单个 XMP Profile"""
        profile = XMPProfile()

        if start_offset + 10 > len(self.data):
            return profile

        # 检查是否启用
        voltage_byte = self.data[start_offset]
        if voltage_byte == 0 or voltage_byte == 0xFF:
            return profile

        profile.enabled = True

        # 电压 (mV)
        profile.voltage = 1.2 + (voltage_byte & 0x3F) * 0.005

        # tCK
        tck_mtb = self.data[start_offset + 1]
        if tck_mtb > 0:
            profile.tCK = tck_mtb * MTB / 1000
            profile.frequency = int(2000 / profile.tCK) if profile.tCK > 0 else 0

        # 时序
        profile.CL = self.data[start_offset + 6] & 0x1F if start_offset + 6 < len(self.data) else 0
        profile.tRCD = self.data[start_offset + 7] if start_offset + 7 < len(self.data) else 0
        profile.tRP = self.data[start_offset + 8] if start_offset + 8 < len(self.data) else 0
        profile.tRAS = self.data[start_offset + 9] if start_offset + 9 < len(self.data) else 0

        return profile

    def get_timing_string(self) -> str:
        """获取时序字符串（如 CL16-18-18-36）"""
        timing = self.parse_timings()
        tck = timing.tCK

        if tck <= 0:
            return "Unknown"

        cl = timing.CL if timing.CL > 0 else round(timing.tAA / tck)
        trcd = round(timing.tRCD / tck)
        trp = round(timing.tRP / tck)
        tras = round(timing.tRAS / tck)

        return f"CL{cl}-{trcd}-{trp}-{tras}"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        if not self.is_valid():
            return {"error": "Invalid DDR4 data"}

        capacity = self.parse_capacity()
        timing = self.parse_timings()
        manufacturer = self.parse_manufacturer()
        xmp = self.parse_xmp()

        return {
            "memory_type": self.parse_memory_type(),
            "module_type": self.parse_module_type(),
            "capacity": capacity["capacity_str"],
            "organization": capacity["organization"],
            "speed_grade": self.parse_speed_grade(),
            "voltage": 1.2,
            "manufacturer": manufacturer["name"],
            "part_number": self.parse_part_number(),
            "serial_number": self.parse_serial_number(),
            "manufacturing_date": self.parse_manufacturing_date(),
            "timing_string": self.get_timing_string(),
            "timings": {
                "tCK": f"{timing.tCK:.3f} ns",
                "tAA": f"{timing.tAA:.3f} ns",
                "tRCD": f"{timing.tRCD:.3f} ns",
                "tRP": f"{timing.tRP:.3f} ns",
                "tRAS": f"{timing.tRAS:.3f} ns",
                "tRC": f"{timing.tRC:.3f} ns",
                "tRFC1": f"{timing.tRFC1:.1f} ns",
                "CL": timing.CL,
            },
            "supported_cl": self.parse_cas_latencies(),
            "xmp": xmp,
            "capacity_details": capacity,
        }

    def parse(self) -> str:
        """
        解析并返回格式化的信息字符串
        （兼容旧版本接口）
        """
        if not self.is_valid():
            return "数据无效或非DDR4内存"

        info = self.to_dict()
        lines = [
            f"内存类型: {info['memory_type']}",
            f"模组类型: {info['module_type']}",
            f"容量: {info['capacity']} ({info['organization']})",
            f"速度等级: {info['speed_grade']} MT/s",
            f"时序: {info['timing_string']}",
            f"制造商: {info['manufacturer']}",
            f"部件号: {info['part_number']}",
            f"序列号: {info['serial_number']}",
            f"生产日期: {info['manufacturing_date']}",
        ]

        if info['xmp']['supported']:
            lines.append(f"XMP支持: 是 ({info['xmp']['version']})")
            for profile in info['xmp']['profiles']:
                lines.append(f"  {profile['name']}: {profile['frequency']} MT/s @ {profile['voltage']:.2f}V ({profile['timings']})")
        else:
            lines.append("XMP支持: 否")

        return "\n".join(lines)
