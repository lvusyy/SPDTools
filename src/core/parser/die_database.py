"""
Die Type Database
Inference database for identifying die types and process nodes from part numbers

SK Hynix Part Number Structure (DDR4):
  HMA [X] [YY] [Z] R7 [AA] [R] [CC] N - [SPEED]
  │    │   │    │  │    │   │   │  │     └── Speed bin
  │    │   │    │  │    │   │   │  └── Generation
  │    │   │    │  │    │   │   └── Rank/Stack config
  │    │   │    │  │    │   └── Row address bits
  │    │   │    │  │    └── Module type code
  │    │   │    │  └── Fixed "R7"
  │    │   │    └── Die revision (A=A-die, B=B-die, C=C-die, etc.)
  │    │   └── Capacity code (e.g., 41=4GB, 42=8GB, 81=8GB, 82=16GB, 84=32GB, BA=64GB, AG=128GB)
  │    └── First letter indicates general product line
  └── SK Hynix Memory prefix

Example: HMABAGR7A4R4N-WR
  - HMA = SK Hynix DDR4
  - B = Product variant
  - AG = 128GB capacity code
  - R7 = fixed
  - A = A-die (21nm Deneb)
  - 4 = 4-bit width (x4)
  - R4 = Registered DIMM, 4 ranks
  - N = Generation
  - WR = DDR4-2933 (1466 MHz)

Die revision is at position 9 (0-indexed) in the part number.
"""

from typing import Dict, Optional


# Die revision mapping for SK Hynix (position 9 in part number)
HYNIX_DIE_REVISION = {
    "A": {"die_type": "A-die", "process": "21nm (Deneb)", "manufacturer": "SK Hynix"},
    "B": {"die_type": "B-die", "process": "18nm (M17B)", "manufacturer": "SK Hynix"},
    "C": {"die_type": "C-die", "process": "1ynm", "manufacturer": "SK Hynix"},
    "D": {"die_type": "D-die", "process": "1znm", "manufacturer": "SK Hynix"},
    "E": {"die_type": "E-die", "process": "1anm", "manufacturer": "SK Hynix"},
    "F": {"die_type": "F-die", "process": "25nm (Legacy)", "manufacturer": "SK Hynix"},
    "J": {"die_type": "J-die", "process": "20nm", "manufacturer": "SK Hynix"},
    "M": {"die_type": "M-die", "process": "20nm", "manufacturer": "SK Hynix"},
}

# Die database mapping part number prefixes to die types and process information
# Note: These are fallback patterns when specific parsing isn't available
DIE_DATABASE = {
    # Samsung patterns (more reliable prefix matching)
    "M378A": {"die_type": "A-die", "process": "20nm", "manufacturer": "Samsung"},
    "M378B": {"die_type": "B-die", "process": "18nm", "manufacturer": "Samsung"},
    "M391A": {"die_type": "A-die", "process": "20nm", "manufacturer": "Samsung"},
    "M391B": {"die_type": "B-die", "process": "18nm", "manufacturer": "Samsung"},
    "M393A": {"die_type": "A-die", "process": "20nm", "manufacturer": "Samsung"},
    "M393B": {"die_type": "B-die", "process": "18nm", "manufacturer": "Samsung"},
    "M386A": {"die_type": "B-die", "process": "18nm", "manufacturer": "Samsung"},
    "M386B": {"die_type": "B-die", "process": "18nm", "manufacturer": "Samsung"},

    # Micron patterns
    "MTA": {"die_type": "Rev-A", "process": "20nm", "manufacturer": "Micron"},
    "MTB": {"die_type": "Rev-B", "process": "16nm", "manufacturer": "Micron"},
    "MTC": {"die_type": "Rev-C", "process": "14nm", "manufacturer": "Micron"},
}


def _parse_hynix_die_revision(part_number: str) -> Optional[Dict[str, str]]:
    """
    Parse SK Hynix part number to extract die revision

    SK Hynix DDR4 part numbers have die revision at position 9 (after 'R7' segment)
    Examples:
      - HMABAGR7A4R4N-WR: position 9 = 'A' -> A-die
      - HMA82GR7AFR8N-VK: position 9 = 'F' -> Unknown (older format)

    Args:
        part_number: SK Hynix part number

    Returns:
        Die info dictionary or None
    """
    if not part_number or len(part_number) < 10:
        return None

    # Clean and validate
    part_number = part_number.strip().upper()

    # Check for HMA prefix (SK Hynix DDR4)
    if not part_number.startswith("HMA"):
        return None

    # Look for 'R7' marker which precedes die revision
    r7_pos = part_number.find("R7")
    if r7_pos == -1 or r7_pos + 2 >= len(part_number):
        return None

    # Die revision is right after 'R7'
    die_char = part_number[r7_pos + 2]

    if die_char in HYNIX_DIE_REVISION:
        return HYNIX_DIE_REVISION[die_char].copy()

    return None


def infer_die_type(part_number: str, manufacturer: str = "") -> Optional[Dict[str, str]]:
    """
    Infer die type and process node from part number

    Args:
        part_number: Memory module part number
        manufacturer: Manufacturer name (optional, for validation)

    Returns:
        Dictionary with die_type and process, or None if no match
    """
    if not part_number:
        return None

    # Clean part number
    part_number = part_number.strip().upper()

    # Try SK Hynix specific parsing first
    if part_number.startswith("HMA"):
        result = _parse_hynix_die_revision(part_number)
        if result:
            return result

    # Fall back to prefix database matching
    # Try matching from longest prefix to shortest
    for length in range(min(len(part_number), 6), 2, -1):
        prefix = part_number[:length]
        if prefix in DIE_DATABASE:
            match = DIE_DATABASE[prefix].copy()
            # Validate manufacturer if provided
            if manufacturer and "manufacturer" in match:
                if manufacturer.lower() not in match["manufacturer"].lower():
                    continue
            return match

    return None


def get_die_description(die_info: Optional[Dict[str, str]], density_gb: float) -> str:
    """
    Format die information for display

    Args:
        die_info: Result from infer_die_type()
        density_gb: Die density in Gb

    Returns:
        Formatted string like "16 Gb B-die (18nm)" or just "16 Gb"
    """
    if density_gb <= 0:
        return "Unknown"

    # Format density
    density_str = f"{int(density_gb)} Gb" if density_gb >= 1 else f"{int(density_gb * 1024)} Mb"

    # Add die type if available
    if die_info:
        die_type = die_info.get("die_type", "")
        process = die_info.get("process", "")

        if die_type and process:
            return f"{density_str} {die_type} ({process})"
        elif die_type:
            return f"{density_str} {die_type}"

    return density_str
