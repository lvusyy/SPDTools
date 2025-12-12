"""
JEDEC 制造商数据库
基于 JEDEC JEP106 标准
"""

# 制造商 ID 映射表 (Bank, ID) -> Name
# Bank 从 1 开始，ID 是去除奇偶校验位后的值
MANUFACTURERS = {
    # Bank 1
    (1, 0x2C): "Micron Technology",
    (1, 0x89): "Intel",
    (1, 0xCE): "Samsung",
    (1, 0xAD): "SK Hynix",
    (1, 0x01): "AMD",
    (1, 0x98): "Toshiba",
    (1, 0xC1): "Infineon",
    (1, 0x20): "STMicroelectronics",
    (1, 0x1C): "Mitsubishi",
    (1, 0x04): "Fujitsu",
    (1, 0x07): "Hitachi",
    (1, 0xDA): "Winbond",
    (1, 0xC2): "Macronix",
    (1, 0xBF): "SST",
    (1, 0x9D): "ISSI",
    (1, 0x37): "AMIC",
    (1, 0x8C): "EON",
    (1, 0xA1): "Fudan Microelectronics",
    (1, 0x1F): "Atmel",

    # Bank 2
    (2, 0x9E): "Corsair",
    (2, 0xB0): "Sharp",
    (2, 0xBA): "PNY",
    (2, 0x4F): "Transcend",
    (2, 0xFE): "ELPIDA",
    (2, 0x0B): "Nanya",
    (2, 0x45): "SanDisk",
    (2, 0x94): "ESMT",
    (2, 0x51): "Qimonda",
    (2, 0x7A): "Apacer",
    (2, 0x83): "Kingmax",
    (2, 0x25): "Kingmax",
    (2, 0xF7): "Silicon Power",
    (2, 0x98): "Kingston",  # Kingston Technology

    # Bank 3
    (3, 0x9B): "Mushkin",
    (3, 0xCB): "A-DATA",
    (3, 0xF1): "Avant",
    (3, 0xCD): "G.Skill",
    (3, 0xEF): "Team Group",
    (3, 0x7F): "Patriot",
    (3, 0x4A): "GeIL",
    (3, 0x08): "Crucial",

    # Bank 4
    (4, 0x03): "OCZ",
    (4, 0xEF): "Crucial (Lexar)",
    (4, 0x34): "Super Talent",
    (4, 0x43): "Ramaxel",
    (4, 0x85): "Spectek",
    (4, 0xC8): "Aeneon",

    # Bank 5
    (5, 0x51): "SMART",
    (5, 0x57): "ATRM",
    (5, 0x9A): "Swissbit",
    (5, 0xB3): "ATP Electronics",
    (5, 0x94): "Innodisk",

    # Bank 6
    (6, 0x43): "Ramaxel Technology",
    (6, 0xCE): "Samsung",
    (6, 0x51): "SMART Modular",
    (6, 0x85): "Wintec",
    (6, 0xC1): "V-Color",

    # Bank 7
    (7, 0xCE): "Samsung",
    (7, 0xAD): "SK Hynix",
    (7, 0x2C): "Micron",

    # Bank 8
    (8, 0xCE): "Samsung",
    (8, 0xC8): "Shanghai Huahong",
    (8, 0x21): "Longsys",

    # Bank 9
    (9, 0xCE): "Samsung",
    (9, 0x2C): "Micron",
    (9, 0xAD): "SK Hynix",
    (9, 0x48): "UniIC",
    (9, 0xC9): "ChangXin Memory (CXMT)",
    (9, 0xCA): "Yangtze Memory (YMTC)",
}

# 常见制造商简称映射
MANUFACTURER_ALIASES = {
    "Samsung": "Samsung",
    "SK Hynix": "Hynix",
    "Micron Technology": "Micron",
    "Crucial": "Crucial",
    "Corsair": "Corsair",
    "G.Skill": "G.Skill",
    "Kingston": "Kingston",
    "Team Group": "Team",
    "A-DATA": "ADATA",
}


def decode_bank_id(first_byte: int, second_byte: int) -> tuple:
    """
    解码制造商 ID

    Args:
        first_byte: SPD Byte 320 (continuation code)
        second_byte: SPD Byte 321 (manufacturer ID)

    Returns:
        (bank, id) 元组
    """
    # 计算 bank 数（continuation code 中 0x7F 的数量 + 1）
    bank = 1
    if first_byte == 0x7F:
        # 需要检查 continuation code
        # 简化处理：假设 first_byte 直接表示 bank
        bank = 1
    else:
        # first_byte 本身可能包含 bank 信息
        continuation_count = 0
        byte_val = first_byte
        while byte_val == 0x7F:
            continuation_count += 1
            # 在实际实现中需要读取更多字节
            break
        bank = continuation_count + 1

    # 去除奇偶校验位
    manufacturer_id = second_byte & 0x7F

    return (bank, manufacturer_id)


def get_manufacturer_name(first_byte: int, second_byte: int) -> str:
    """
    获取制造商名称

    Args:
        first_byte: SPD Byte 320
        second_byte: SPD Byte 321

    Returns:
        制造商名称，未知返回十六进制表示
    """
    # 尝试直接匹配（不考虑 bank）
    for (bank, mid), name in MANUFACTURERS.items():
        if second_byte == mid or (second_byte & 0x7F) == mid:
            return name

    # 尝试完整解码
    bank, mid = decode_bank_id(first_byte, second_byte)
    if (bank, mid) in MANUFACTURERS:
        return MANUFACTURERS[(bank, mid)]

    # 未知制造商
    return f"Unknown (0x{first_byte:02X}{second_byte:02X})"


def get_manufacturer_short_name(name: str) -> str:
    """获取制造商简称"""
    return MANUFACTURER_ALIASES.get(name, name)


# 常用制造商列表（用于下拉选择）
COMMON_MANUFACTURERS = [
    "Samsung",
    "SK Hynix",
    "Micron Technology",
    "Crucial",
    "Corsair",
    "G.Skill",
    "Kingston",
    "Team Group",
    "A-DATA",
    "Patriot",
    "GeIL",
    "Ramaxel Technology",
    "Nanya",
]


def get_manufacturer_id(name: str) -> tuple:
    """
    根据制造商名称获取 ID

    Args:
        name: 制造商名称

    Returns:
        (first_byte, second_byte) 元组，未找到返回 (0x00, 0x00)
    """
    for (bank, mid), mfr_name in MANUFACTURERS.items():
        if mfr_name == name:
            # first_byte 表示 bank (简化处理)
            first_byte = bank - 1 if bank > 1 else 0x00
            # second_byte 是制造商 ID，加上奇偶校验位
            # 简化处理：直接使用原始 ID
            second_byte = mid | 0x80  # 设置最高位（奇偶校验）
            return (first_byte, second_byte)
    return (0x00, 0x00)
