# SPD Studio v2.0

DDR4 内存 SPD 数据读写工具，支持查看、编辑和写入内存条的 SPD (Serial Presence Detect) 数据。

## 功能特性

- **SPD 数据读取**: 从内存条读取完整的 512 字节 SPD 数据
- **SPD 数据写入**: 将修改后的 SPD 数据写入内存条
- **十六进制编辑器**: 直观的 HEX 视图，支持范围选择和多种复制格式
- **参数解析**: 自动解析并显示内存参数（容量、速度、时序等）
- **XMP 配置**: 支持 XMP 2.0 配置文件的查看
- **制造商信息**: 支持编辑制造商、部件号、序列号等信息
- **数据导入/导出**: 支持 BIN 文件的导入和导出

## 兼容硬件

### SPD 读写器

本工具设计用于基于 CH341 或兼容芯片的 USB SPD 读写器。

**默认支持的设备参数：**
- **Vendor ID (VID)**: `0x0483`
- **Product ID (PID)**: `0x1230`

**兼容设备类型：**
- CH341A USB 编程器（带 SPD 读写功能）
- USB SPD 读写器/编程器
- 其他兼容 HID 协议的 SPD 读写设备

**通信协议：**
- 接口类型: USB HID
- I2C 地址: `0x50` (标准 SPD EEPROM 地址)
- 数据格式: 512 字节 (Page 0: 0-255, Page 1: 256-511)
- 页面切换命令:
  - Page 0: `BT-I2C2WR360001`
  - Page 1: `BT-I2C2WR370001`

### 支持的内存类型

- **DDR4 SDRAM** (完整支持)
  - UDIMM
  - RDIMM
  - SO-DIMM
  - LRDIMM

### XMP 支持

- XMP 2.0 配置文件解析
- 支持 Profile 1 和 Profile 2
- 显示频率、电压、时序参数

## 系统要求

- **操作系统**: Windows 10/11, Linux, macOS
- **Python**: 3.8 或更高版本
- **依赖库**:
  - `customtkinter` - 现代化 GUI 框架
  - `hidapi` - USB HID 设备通信

## 安装

### 1. 克隆仓库

```bash
git clone https://github.com/yourusername/SPDTools.git
cd SPDTools
```

### 2. 安装依赖

```bash
pip install customtkinter hidapi
```

### 3. 运行程序

```bash
python main.py
```

## 使用说明

### 连接设备

1. 将 SPD 读写器连接到电脑 USB 端口
2. 将内存条安装到读写器上
3. 启动程序，点击 "连接设备" 按钮

### 读取 SPD

1. 确保设备已连接
2. 点击 "读取 SPD" 按钮
3. 等待读取完成（约 10-15 秒）
4. 数据将显示在各个选项卡中

### 编辑数据

#### 基本信息编辑
- 在 "详细参数" 选项卡中点击 "Edit" 按钮
- 可编辑：制造商、部件号、序列号、模组类型等

#### 十六进制编辑
- 在 "HEX 视图" 选项卡中双击字节进行编辑
- 支持键盘直接输入十六进制值
- 右键菜单支持多种复制格式

### 写入 SPD

1. 完成编辑后，点击 "写入 SPD" 按钮
2. 确认写入操作
3. 等待写入完成
4. **重要**: 写入完成后需要重启电脑使更改生效

### 导入/导出

- **导出**: 文件 → 导出 SPD → 保存为 .bin 文件
- **导入**: 文件 → 导入 SPD → 选择 .bin 文件

## 项目结构

```
SPDTools/
├── main.py                 # 程序入口
├── README.md               # 本文档
├── src/
│   ├── __init__.py
│   ├── core/               # 核心逻辑
│   │   ├── driver.py       # 硬件驱动层
│   │   ├── model.py        # 数据模型
│   │   └── parser/         # SPD 解析器
│   │       ├── ddr4.py     # DDR4 解析
│   │       └── manufacturers.py  # 制造商数据库
│   ├── gui/                # 图形界面
│   │   ├── app.py          # 主应用程序
│   │   ├── tabs/           # 选项卡页面
│   │   └── widgets/        # UI 组件
│   └── utils/              # 工具函数
│       └── constants.py    # 常量定义
└── *.bin                   # 示例 SPD 数据文件
```

## 技术规范

### SPD 数据布局 (DDR4)

| 字节范围 | 内容 |
|---------|------|
| 0-127 | 基本配置参数 |
| 128-255 | 模组特定参数 |
| 320-383 | 制造商信息 |
| 384-511 | XMP 配置 |

### 主要偏移量

| 偏移 | 描述 |
|-----|------|
| 0x000 | SPD 字节使用量 |
| 0x002 | DRAM 设备类型 (0x0C = DDR4) |
| 0x003 | 模组类型 |
| 0x004 | 密度和 Bank |
| 0x012 | 最小时钟周期 (tCK) |
| 0x140 | 制造商 ID |
| 0x149 | 部件号 (20 字符) |
| 0x180 | XMP 头部 |

## 注意事项

1. **数据备份**: 修改前请务必导出原始 SPD 数据作为备份
2. **兼容性**: 不当的 SPD 修改可能导致系统无法启动
3. **XMP 时序**: 修改 XMP 时序需要了解内存超频知识
4. **硬件保护**: 部分内存条的 SPD 可能有写保护

## 故障排除

### 设备无法连接

1. 检查 USB 连接是否稳固
2. 确认驱动程序已正确安装
3. 尝试更换 USB 端口
4. 检查设备管理器中是否识别到 HID 设备

### 读取数据全为零

1. 检查内存条是否正确安装在读写器上
2. 确认内存条的金手指接触良好
3. 尝试重新插拔内存条

### 写入后系统无法启动

1. 使用读写器恢复备份的 SPD 数据
2. 检查修改的参数是否在合理范围内

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 参考资料

- [JEDEC SPD 标准](https://www.jedec.org/)
- [DDR4 SPD 规范 (JESD21-C)](https://www.jedec.org/standards-documents/docs/jesd21-c)
- [Intel XMP 2.0 规范](https://www.intel.com/content/www/us/en/gaming/extreme-memory-profile-xmp.html)
