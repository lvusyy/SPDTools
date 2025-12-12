#!/usr/bin/env python3
"""
SPD Studio v2.0
DDR4 内存 SPD 读写工具

使用方法:
    python main.py

依赖:
    pip install customtkinter hidapi
"""

import sys
import os

# 确保可以导入 src 模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.gui.app import SPDApp


def main():
    """主入口"""
    app = SPDApp()
    app.mainloop()


if __name__ == "__main__":
    main()
