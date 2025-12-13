"""
DDR4 SPD 解析器
根据 JEDEC 标准解析 DDR4 内存 SPD 数据
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .manufacturers import get_manufacturer_name
from .die_database import infer_die_type, get_die_description
from ...utils.constants import (
    SPD_SIZE, SPD_BYTES, DDR4_TYPE, MODULE_TYPES,
    DENSITY_MAP, DEVICE_WIDTH, ROW_BITS, COL_BITS,
    MTB, FTB, SPEED_GRADES, XMP_MAGIC,
    PACKAGE_TYPES, DIE_COUNTS, SIGNAL_LOADING, BANKS_PER_GROUP
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
    tRFC2: float = 0    # Refresh Recovery 2x mode (ns)
    tRFC4: float = 0    # Refresh Recovery 4x mode (ns)
    tFAW: float = 0     # Four Activate Window (ns)
    tRRD_S: float = 0   # Activate to Activate (different bank group)
    tRRD_L: float = 0   # Activate to Activate (same bank group)
    tCCD_L: float = 0   # CAS to CAS (same bank group)
    tWR: float = 0      # Write Recovery (ns)
    tWTR_S: float = 0   # Write to Read (different bank group) (ns)
    tWTR_L: float = 0   # Write to Read (same bank group) (ns)
    CL: int = 0         # CAS Latency (cycles)


@dataclass
class DieInfo:
    """Die/Package Information"""
    density_gb: float = 0      # Die density in Gb
    die_count: int = 1         # Number of dies
    package_type: str = ""     # Monolithic or 3DS
    signal_loading: str = ""   # Signal loading type
    organization: str = ""     # e.g., "2048 Mb x8 (64M x 8 x 32 banks)"


@dataclass
class BankConfig:
    """Bank Configuration"""
    bank_groups: int = 4       # Number of bank groups
    banks_per_group: int = 4   # Banks per group (always 4 for DDR4)
    total_banks: int = 16      # Total banks


@dataclass
class AddressingInfo:
    """Memory Addressing Information"""
    row_bits: int = 0          # Number of row address bits
    col_bits: int = 0          # Number of column address bits
    page_size_bytes: int = 0   # Page size = 2^col_bits * device_width / 8


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
        package_byte = self.data[SPD_BYTES.PACKAGE_TYPE]

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

        # 3DS (Non-Monolithic) package detection from byte 6
        # Bit 7: Package Type (0 = Monolithic, 1 = Non-Monolithic/3DS)
        # Bits 6:4: Die count for 3DS (0=1, 1=2, 2=3, 3=4, 4=5, 5=6, 6=7, 7=8)
        is_3ds = (package_byte >> 7) & 0x01
        die_count_code = (package_byte >> 4) & 0x07
        die_count = DIE_COUNTS.get(die_count_code, 1) if is_3ds else 1

        # 计算总容量 (GB)
        # 标准容量 = 密度 * (64 / 设备宽度) * Rank数 / 8
        # 对于 3DS 封装，需要乘以堆叠的 Die 数量
        # Formula: capacity_gb = density_gb * (bus_width / device_width) * ranks * die_count / 8
        if device_width > 0:
            capacity_gb = density_gb * (bus_width / device_width) * ranks * die_count / 8
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
            "organization": f"{ranks}Rx{device_width}",
            "is_3ds": is_3ds,
            "die_count": die_count
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

        # tRFC2 (bytes 32-33)
        trfc2 = (self.data[SPD_BYTES.TRFC2_HIGH] << 8) + self.data[SPD_BYTES.TRFC2_LOW]
        timing.tRFC2 = trfc2 * MTB / 1000

        # tRFC4 (bytes 34-35)
        trfc4 = (self.data[SPD_BYTES.TRFC4_HIGH] << 8) + self.data[SPD_BYTES.TRFC4_LOW]
        timing.tRFC4 = trfc4 * MTB / 1000

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

        # tWR (bytes 41-42, uses high nibble + low byte)
        twr_high = (self.data[SPD_BYTES.TWR_MIN_HIGH] & 0x0F) << 8
        twr_low = self.data[SPD_BYTES.TWR_MIN_LOW]
        timing.tWR = (twr_high + twr_low) * MTB / 1000

        # tWTR_S (byte 43)
        timing.tWTR_S = self.data[SPD_BYTES.TWTR_S_MIN] * MTB / 1000

        # tWTR_L (byte 44)
        timing.tWTR_L = self.data[SPD_BYTES.TWTR_L_MIN] * MTB / 1000

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

    def parse_die_info(self) -> DieInfo:
        """解析 Die 和封装信息"""
        density_byte = self.data[SPD_BYTES.DENSITY_BANKS]
        package_byte = self.data[SPD_BYTES.PACKAGE_TYPE]
        org_byte = self.data[SPD_BYTES.MODULE_ORG]

        # Die density from byte 4, bits 3:0
        density_code = density_byte & 0x0F
        density_gb = DENSITY_MAP.get(density_code, 0)

        # Package type from byte 6, bit 7
        is_3ds = (package_byte >> 7) & 0x01
        package_type = PACKAGE_TYPES.get(is_3ds, "Unknown")

        # Die count from byte 6, bits 6:4
        die_count_code = (package_byte >> 4) & 0x07
        die_count = DIE_COUNTS.get(die_count_code, 1)

        # Signal loading from byte 6, bits 1:0
        signal_code = package_byte & 0x03
        signal_loading = SIGNAL_LOADING.get(signal_code, "Not specified")

        # Device width for organization string
        device_width_code = org_byte & 0x07
        device_width = DEVICE_WIDTH.get(device_width_code, 8)

        # Bank groups
        bg_code = (density_byte >> 6) & 0x03
        bank_groups = 4 if bg_code == 0 else 2

        # Organization string (e.g., "2048 Mb x8 (64M x 8 x 32 banks)")
        density_mb = int(density_gb * 1024)
        banks_total = bank_groups * BANKS_PER_GROUP
        organization = f"{density_mb} Mb x{device_width} ({density_mb//8}M x {device_width} x {banks_total} banks)"

        return DieInfo(
            density_gb=density_gb,
            die_count=die_count,
            package_type=package_type,
            signal_loading=signal_loading,
            organization=organization
        )

    def parse_bank_config(self) -> BankConfig:
        """解析 Bank 组配置"""
        density_byte = self.data[SPD_BYTES.DENSITY_BANKS]

        # Bank groups from byte 4, bits 7:6
        bg_code = (density_byte >> 6) & 0x03
        bank_groups = 4 if bg_code == 0 else 2

        banks_per_group = BANKS_PER_GROUP  # Always 4 for DDR4
        total_banks = bank_groups * banks_per_group

        return BankConfig(
            bank_groups=bank_groups,
            banks_per_group=banks_per_group,
            total_banks=total_banks
        )

    def parse_addressing_info(self) -> AddressingInfo:
        """解析详细地址信息"""
        addressing_byte = self.data[SPD_BYTES.ADDRESSING]
        org_byte = self.data[SPD_BYTES.MODULE_ORG]

        # Row address bits from byte 5, bits 5:3
        row_code = (addressing_byte >> 3) & 0x07
        row_bits = ROW_BITS.get(row_code, 0)

        # Column address bits from byte 5, bits 2:0
        col_code = addressing_byte & 0x07
        col_bits = COL_BITS.get(col_code, 0)

        # Device width for page size calculation
        device_width_code = org_byte & 0x07
        device_width = DEVICE_WIDTH.get(device_width_code, 8)

        # Page size = 2^col_bits * device_width / 8 (in bytes)
        page_size = (2 ** col_bits) * device_width // 8

        return AddressingInfo(
            row_bits=row_bits,
            col_bits=col_bits,
            page_size_bytes=page_size
        )

    def parse_ecc_info(self) -> Dict[str, Any]:
        """解析 ECC/总线宽度扩展信息"""
        width_byte = self.data[SPD_BYTES.BUS_WIDTH]

        # Primary bus width from bits 2:0
        primary_code = width_byte & 0x07
        primary_width = 8 * (1 << primary_code)  # 8, 16, 32, 64

        # Bus width extension from bits 4:3
        ext_code = (width_byte >> 3) & 0x03
        extension_width = {
            0b00: 0,   # No extension
            0b01: 8,   # 8-bit extension (ECC)
            0b10: 16,  # Reserved
            0b11: 0    # Reserved
        }.get(ext_code, 0)

        total_width = primary_width + extension_width
        has_ecc = extension_width > 0

        return {
            "primary_width": primary_width,
            "extension_width": extension_width,
            "total_width": total_width,
            "has_ecc": has_ecc,
            "ecc_type": "ECC" if has_ecc else "Non-ECC"
        }

    def parse_thermal_sensor(self) -> Dict[str, Any]:
        """解析温度传感器状态"""
        thermal_byte = self.data[SPD_BYTES.THERMAL_SENSOR]

        # Bit 7: Thermal sensor
        has_sensor = bool((thermal_byte >> 7) & 0x01)

        return {
            "present": has_sensor,
            "description": "Thermal Sensor Present" if has_sensor else "No Thermal Sensor"
        }

    def parse_dram_manufacturer(self) -> Dict[str, str]:
        """解析 DRAM 制造商（与模组制造商分离）"""
        if len(self.data) <= SPD_BYTES.DRAM_MANUFACTURER_ID_SECOND:
            return {"name": "Unknown", "id_bytes": "0x0000"}

        first_byte = self.data[SPD_BYTES.DRAM_MANUFACTURER_ID_FIRST]
        second_byte = self.data[SPD_BYTES.DRAM_MANUFACTURER_ID_SECOND]

        manufacturer = get_manufacturer_name(first_byte, second_byte)

        return {
            "name": manufacturer,
            "id_bytes": f"0x{first_byte:02X}{second_byte:02X}",
        }

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

        # XMP 2.0 header 为 0x0C
        if xmp_header == XMP_MAGIC:
            result["supported"] = True
            result["version"] = "2.0"

            # Profile 启用状态 (Byte 386)
            profile_enabled = self.data[SPD_BYTES.XMP_PROFILE_ENABLED] if len(self.data) > SPD_BYTES.XMP_PROFILE_ENABLED else 0

            # 解析 Profile 1 (从 Byte 393 开始)
            profile1 = self._parse_xmp_profile(SPD_BYTES.XMP_PROFILE1_START, 1)
            if profile1.enabled:
                result["profiles"].append({
                    "name": "Profile 1",
                    "voltage": profile1.voltage,
                    "frequency": profile1.frequency,
                    "timings": f"CL{profile1.CL}-{profile1.tRCD}-{profile1.tRP}-{profile1.tRAS}"
                })

            # 解析 Profile 2 (从 Byte 440 开始)
            if len(self.data) >= 487:
                profile2 = self._parse_xmp_profile(SPD_BYTES.XMP_PROFILE2_START, 2)
                if profile2.enabled:
                    result["profiles"].append({
                        "name": "Profile 2",
                        "voltage": profile2.voltage,
                        "frequency": profile2.frequency,
                        "timings": f"CL{profile2.CL}-{profile2.tRCD}-{profile2.tRP}-{profile2.tRAS}"
                    })

        return result

    def _parse_xmp_profile(self, start_offset: int, profile_num: int) -> XMPProfile:
        """
        解析单个 XMP Profile

        根据实际数据分析，XMP 2.0 Profile 布局:
        原始数据: A3 00 00 05 FF FF 03 00 50 64 64 10 BD 22 30 11 F0 0A 20 08

        +0: Voltage (VDD) - 0xA3 = 1.375V
        +3: tCK (MTB) - 0x05 = 5 * 125ps = 625ps = 3200 MT/s
        +8: tAA (MTB) - 0x50 = 80 * 125ps = 10000ps = 10ns
        +9: tRCD (MTB) - 0x64 = 100 * 125ps = 12500ps = 12.5ns
        +10: tRP (MTB) - 0x64 = 100 * 125ps = 12500ps = 12.5ns
        +11-12: tRAS upper/lower
        """
        profile = XMPProfile()

        if start_offset + 15 > len(self.data):
            return profile

        # 调试：打印 XMP Profile 原始数据
        raw_bytes = self.data[start_offset:start_offset + 20]
        print(f"[DEBUG XMP] Profile {profile_num} raw bytes at 0x{start_offset:03X}: {' '.join(f'{b:02X}' for b in raw_bytes)}")

        # 电压字节
        voltage_byte = self.data[start_offset]
        if voltage_byte == 0 or voltage_byte == 0xFF:
            print(f"[DEBUG XMP] Profile {profile_num} disabled (voltage_byte=0x{voltage_byte:02X})")
            return profile

        profile.enabled = True

        # 电压解析: VDD = 1.20V + (voltage_byte[5:0] * 5mV)
        # 0xA3 & 0x3F = 0x23 = 35, 35 * 5mV = 175mV, 1.2V + 0.175V = 1.375V
        # 但 Thaiphoon 显示 1.35V，所以可能是不同的计算方式
        # 0x1E = 30, 30 * 5mV = 150mV, 1.2V + 0.15V = 1.35V
        profile.voltage = 1.2 + (voltage_byte & 0x3F) * 0.005
        print(f"[DEBUG XMP] Profile {profile_num} voltage: {profile.voltage:.3f}V (byte=0x{voltage_byte:02X})")

        # tCK - 尝试多个位置找到合理的 tCK 值
        tck_candidates = [
            (3, "offset+3"),  # 根据实际数据，tCK 在 offset +3
            (2, "offset+2"),
            (1, "offset+1"),
        ]

        for tck_offset, desc in tck_candidates:
            tck_mtb = self.data[start_offset + tck_offset] if start_offset + tck_offset < len(self.data) else 0
            if tck_mtb > 0 and tck_mtb < 20:  # tCK 通常在 4-15 范围 (DDR4-1600 到 DDR4-4000)
                profile.tCK = tck_mtb * MTB / 1000  # 转换为 ns
                profile.frequency = int(2000 / profile.tCK) if profile.tCK > 0 else 0
                print(f"[DEBUG XMP] Profile {profile_num} tCK from {desc}: byte=0x{tck_mtb:02X}, tCK={profile.tCK:.3f}ns, freq={profile.frequency} MT/s")
                if 1600 <= profile.frequency <= 6000:
                    break

        if profile.frequency < 1600 or profile.frequency > 6000:
            print(f"[DEBUG XMP] Profile {profile_num} WARNING: Could not find valid tCK")
            profile.frequency = 0

        # 时序参数
        # tAA (CAS Latency Time) 在 offset +8
        taa_byte = self.data[start_offset + 8] if start_offset + 8 < len(self.data) else 0
        print(f"[DEBUG XMP] Profile {profile_num} tAA raw: 0x{taa_byte:02X} ({taa_byte})")

        # CL = tAA / tCK
        if profile.tCK > 0 and taa_byte > 0:
            taa_ns = taa_byte * MTB / 1000
            profile.CL = round(taa_ns / profile.tCK)
            print(f"[DEBUG XMP] Profile {profile_num} CL: tAA={taa_ns:.3f}ns / tCK={profile.tCK:.3f}ns = CL{profile.CL}")

        # tRCD 在 offset +9
        trcd_byte = self.data[start_offset + 9] if start_offset + 9 < len(self.data) else 0
        if profile.tCK > 0 and trcd_byte > 0:
            trcd_ns = trcd_byte * MTB / 1000
            profile.tRCD = round(trcd_ns / profile.tCK)
            print(f"[DEBUG XMP] Profile {profile_num} tRCD: {trcd_ns:.3f}ns = {profile.tRCD} cycles")

        # tRP 在 offset +10
        trp_byte = self.data[start_offset + 10] if start_offset + 10 < len(self.data) else 0
        if profile.tCK > 0 and trp_byte > 0:
            trp_ns = trp_byte * MTB / 1000
            profile.tRP = round(trp_ns / profile.tCK)
            print(f"[DEBUG XMP] Profile {profile_num} tRP: {trp_ns:.3f}ns = {profile.tRP} cycles")

        # tRAS 在 offset +11-12 (upper nibble + lower byte)
        tras_upper = (self.data[start_offset + 11] & 0x0F) if start_offset + 11 < len(self.data) else 0
        tras_lower = self.data[start_offset + 12] if start_offset + 12 < len(self.data) else 0
        tras_mtb = (tras_upper << 8) | tras_lower
        if profile.tCK > 0 and tras_mtb > 0:
            tras_ns = tras_mtb * MTB / 1000
            profile.tRAS = round(tras_ns / profile.tCK)
            print(f"[DEBUG XMP] Profile {profile_num} tRAS: raw=0x{tras_upper:X}{tras_lower:02X} ({tras_mtb}), {tras_ns:.3f}ns = {profile.tRAS} cycles")

        print(f"[DEBUG XMP] Profile {profile_num} FINAL: CL{profile.CL}-{profile.tRCD}-{profile.tRP}-{profile.tRAS} @ {profile.frequency} MT/s, {profile.voltage:.3f}V")

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

    def to_dict(self, mode: str = "spd") -> Dict[str, Any]:
        """
        转换为字典格式

        Args:
            mode: 显示模式 ("spd" = 仅 SPD 数据, "read" = 包含推断信息)
        """
        if not self.is_valid():
            return {"error": "Invalid DDR4 data"}

        capacity = self.parse_capacity()
        timing = self.parse_timings()
        manufacturer = self.parse_manufacturer()
        xmp = self.parse_xmp()
        die_info = self.parse_die_info()
        bank_config = self.parse_bank_config()
        addressing = self.parse_addressing_info()
        ecc_info = self.parse_ecc_info()
        thermal = self.parse_thermal_sensor()
        dram_manufacturer = self.parse_dram_manufacturer()

        result = {
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
                "tRFC2": f"{timing.tRFC2:.1f} ns",
                "tRFC4": f"{timing.tRFC4:.1f} ns",
                "tWR": f"{timing.tWR:.3f} ns",
                "tWTR_S": f"{timing.tWTR_S:.3f} ns",
                "tWTR_L": f"{timing.tWTR_L:.3f} ns",
                "CL": timing.CL,
            },
            "supported_cl": self.parse_cas_latencies(),
            "xmp": xmp,
            "capacity_details": capacity,
            "die_info": {
                "density_gb": die_info.density_gb,
                "die_count": die_info.die_count,
                "package_type": die_info.package_type,
                "signal_loading": die_info.signal_loading,
                "organization": die_info.organization,
            },
            "bank_config": {
                "bank_groups": bank_config.bank_groups,
                "banks_per_group": bank_config.banks_per_group,
                "total_banks": bank_config.total_banks,
            },
            "addressing": {
                "row_bits": addressing.row_bits,
                "col_bits": addressing.col_bits,
                "page_size_bytes": addressing.page_size_bytes,
                "page_size_str": f"{addressing.page_size_bytes // 1024} KB" if addressing.page_size_bytes >= 1024 else f"{addressing.page_size_bytes} bytes",
            },
            "ecc_info": ecc_info,
            "thermal_sensor": thermal,
            "dram_manufacturer": dram_manufacturer,
            "display_mode": mode,
        }

        # Add inferred information in "read" mode
        if mode == "read":
            part_number = self.parse_part_number()
            inferred = infer_die_type(part_number, dram_manufacturer["name"])

            result["die_info_inferred"] = {
                "die_type": inferred.get("die_type", "Unknown") if inferred else "Unknown",
                "process_node": inferred.get("process", "Unknown") if inferred else "Unknown",
                "die_description": get_die_description(inferred, die_info.density_gb),
                "inferred": inferred is not None,
            }

        return result

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
