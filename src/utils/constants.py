"""
SPDTools 常量定义
"""

# HID 设备配置
DEFAULT_VID = 0x0483
DEFAULT_PID = 0x1230

# SPD 数据大小
SPD_SIZE = 512
SPD_PAGE_SIZE = 256

# DDR4 SPD 字节偏移定义
class SPD_BYTES:
    # 基本信息 (0-127)
    BYTES_USED = 0          # SPD 使用的字节数
    REVISION = 1            # SPD 修订版本
    DRAM_TYPE = 2           # DRAM 设备类型 (0x0C = DDR4)
    MODULE_TYPE = 3         # 模组类型
    DENSITY_BANKS = 4       # 密度和 Bank 组
    ADDRESSING = 5          # 行列地址位数
    PACKAGE_TYPE = 6        # 封装类型
    OPTIONAL_FEATURES = 7   # 可选功能
    THERMAL_REFRESH = 8     # 热刷新选项
    OTHER_OPTIONAL = 9      # 其他可选功能
    SECONDARY_PACKAGE = 10  # 次要封装类型
    VOLTAGE = 11            # 模组标称电压
    MODULE_ORG = 12         # 模组组织
    BUS_WIDTH = 13          # 模组内存总线宽度
    THERMAL_SENSOR = 14     # 温度传感器

    # 时序参数
    TIMEBASES = 17          # 时间基准
    TCK_MIN = 18            # 最小时钟周期 (MTB)
    TCK_MAX = 19            # 最大时钟周期 (MTB)
    CAS_LATENCIES_1 = 20    # CAS 延迟支持 (第一字节)
    CAS_LATENCIES_2 = 21    # CAS 延迟支持 (第二字节)
    CAS_LATENCIES_3 = 22    # CAS 延迟支持 (第三字节)
    CAS_LATENCIES_4 = 23    # CAS 延迟支持 (第四字节)
    TAA_MIN = 24            # 最小 CAS 延迟时间 (tAA)
    TRCD_MIN = 25           # 最小 RAS 到 CAS 延迟 (tRCD)
    TRP_MIN = 26            # 最小行预充电时间 (tRP)
    TRAS_TRC_HIGH = 27      # tRAS 和 tRC 高位
    TRAS_MIN_LOW = 28       # 最小 Active 到 Precharge (tRAS) 低位
    TRC_MIN_LOW = 29        # 最小 Active 到 Active/Refresh (tRC) 低位
    TRFC1_LOW = 30          # 最小刷新恢复时间 (tRFC1) 低位
    TRFC1_HIGH = 31         # tRFC1 高位
    TRFC2_LOW = 32          # tRFC2 低位
    TRFC2_HIGH = 33         # tRFC2 高位
    TRFC4_LOW = 34          # tRFC4 低位
    TRFC4_HIGH = 35         # tRFC4 高位
    TFAW_HIGH = 36          # tFAW 高位
    TFAW_LOW = 37           # 最小 Four Activate Window (tFAW) 低位
    TRRD_S_MIN = 38         # 最小 tRRD_S
    TRRD_L_MIN = 39         # 最小 tRRD_L
    TCCD_L_MIN = 40         # 最小 tCCD_L

    # 细粒度时序调整 (FTB)
    TCK_MIN_FTB = 125       # tCK Fine Offset
    TAA_MIN_FTB = 123       # tAA Fine Offset
    TRCD_MIN_FTB = 122      # tRCD Fine Offset
    TRP_MIN_FTB = 121       # tRP Fine Offset
    TRC_MIN_FTB = 120       # tRC Fine Offset

    # 制造商信息 (320-383)
    MANUFACTURER_ID_FIRST = 320   # 制造商 ID (第一字节)
    MANUFACTURER_ID_SECOND = 321  # 制造商 ID (第二字节)
    MANUFACTURING_LOCATION = 322  # 制造地点
    MANUFACTURING_YEAR = 323      # 制造年份
    MANUFACTURING_WEEK = 324      # 制造周
    SERIAL_NUMBER_1 = 325         # 序列号字节 1
    SERIAL_NUMBER_2 = 326         # 序列号字节 2
    SERIAL_NUMBER_3 = 327         # 序列号字节 3
    SERIAL_NUMBER_4 = 328         # 序列号字节 4
    PART_NUMBER_START = 329       # 部件号起始位置
    PART_NUMBER_END = 348         # 部件号结束位置 (20字符)
    REVISION_CODE = 349           # 修订代码

    # XMP 配置 (384-511)
    XMP_HEADER = 384              # XMP 头部标识
    XMP_PROFILE1_START = 393      # XMP Profile 1 起始
    XMP_PROFILE2_START = 440      # XMP Profile 2 起始

# DDR4 类型标识
DDR4_TYPE = 0x0C

# 模组类型映射
MODULE_TYPES = {
    0x01: "RDIMM",
    0x02: "UDIMM",
    0x03: "SO-DIMM",
    0x04: "LRDIMM",
    0x05: "Mini-RDIMM",
    0x06: "Mini-UDIMM",
    0x08: "72b-SO-RDIMM",
    0x09: "72b-SO-UDIMM",
    0x0C: "16b-SO-DIMM",
    0x0D: "32b-SO-DIMM",
}

# Bank 组数映射
BANK_GROUPS = {
    0b00: 4,
    0b01: 2,
}

# 密度映射 (Gb)
DENSITY_MAP = {
    0b0000: 0.256,
    0b0001: 0.512,
    0b0010: 1,
    0b0011: 2,
    0b0100: 4,
    0b0101: 8,
    0b0110: 16,
    0b0111: 32,
    0b1000: 12,
    0b1001: 24,
}

# 设备宽度映射
DEVICE_WIDTH = {
    0b000: 4,
    0b001: 8,
    0b010: 16,
    0b011: 32,
}

# 行地址位数映射
ROW_BITS = {
    0b000: 12,
    0b001: 13,
    0b010: 14,
    0b011: 15,
    0b100: 16,
    0b101: 17,
    0b110: 18,
}

# 列地址位数映射
COL_BITS = {
    0b000: 9,
    0b001: 10,
    0b010: 11,
    0b011: 12,
}

# 时间基准 (ps)
MTB = 125    # Medium Time Base = 125ps
FTB = 1      # Fine Time Base = 1ps

# 频率速度等级映射 (tCK -> MT/s)
SPEED_GRADES = {
    (625, 750): 3200,
    (750, 833): 2666,
    (833, 938): 2400,
    (938, 1071): 2133,
    (1071, 1250): 1866,
    (1250, 1500): 1600,
}

# XMP 标识
XMP_MAGIC = 0x0C

# UI 颜色主题
class Colors:
    PRIMARY = "#1f538d"
    SECONDARY = "#444444"
    SUCCESS = "#27ae60"
    WARNING = "#f39c12"
    DANGER = "#c0392b"
    DANGER_HOVER = "#e74c3c"
    BACKGROUND = "#2b2b2b"
    CARD_BG = "#363636"
    TEXT = "#ffffff"
    TEXT_SECONDARY = "#aaaaaa"
    MODIFIED = "#f1c40f"
    HIGHLIGHT = "#3498db"
