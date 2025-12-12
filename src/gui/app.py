"""
SPDTools 主应用窗口
"""

import customtkinter as ctk
import threading
import os
import json
from tkinter import filedialog, messagebox
from typing import Optional
from datetime import datetime

from ..core.driver import SPDDriver
from ..core.model import SPDDataModel, DataChangeEvent, DataChangeType
from ..core.parser import DDR4Parser
from .tabs.overview import OverviewTab
from .tabs.details import DetailsTab
from .tabs.timing import TimingTab
from .tabs.xmp import XMPTab
from .tabs.hex_editor import HexEditorTab
from .tabs.log import LogTab
from ..utils.constants import Colors, SPD_SIZE


class SPDApp(ctk.CTk):
    """SPD Tools 主应用"""

    def __init__(self):
        super().__init__()

        # 设置主题
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # 窗口配置
        self.title("SPD Studio v2.0")
        self.geometry("1100x750")
        self.minsize(900, 600)

        # 核心组件
        self.driver = SPDDriver()
        self.data_model = SPDDataModel()

        # 状态
        self._is_connected = False
        self._operation_in_progress = False

        # 设置布局
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._setup_ui()

        # 监听数据变更
        self.data_model.add_observer(self._on_data_changed)

    def _setup_ui(self):
        """设置界面"""
        self._create_toolbar()
        self._create_main_area()
        self._create_statusbar()

    def _create_toolbar(self):
        """创建工具栏"""
        toolbar = ctk.CTkFrame(self, height=50, fg_color=Colors.CARD_BG)
        toolbar.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        toolbar.grid_columnconfigure(5, weight=1)

        # 左侧按钮组
        btn_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        btn_frame.pack(side="left", padx=15, pady=8)

        self.btn_read = ctk.CTkButton(
            btn_frame,
            text="读取",
            width=80,
            command=self._start_read
        )
        self.btn_read.pack(side="left", padx=(0, 10))

        self.btn_load = ctk.CTkButton(
            btn_frame,
            text="打开文件",
            width=80,
            fg_color=Colors.SECONDARY,
            command=self._load_file
        )
        self.btn_load.pack(side="left", padx=(0, 10))

        self.btn_save = ctk.CTkButton(
            btn_frame,
            text="保存",
            width=80,
            fg_color=Colors.SECONDARY,
            command=self._save_file
        )
        self.btn_save.pack(side="left", padx=(0, 10))

        self.btn_write = ctk.CTkButton(
            btn_frame,
            text="烧录",
            width=80,
            fg_color=Colors.DANGER,
            hover_color=Colors.DANGER_HOVER,
            state="disabled",
            command=self._start_write
        )
        self.btn_write.pack(side="left", padx=(0, 10))

        # 分隔线
        separator = ctk.CTkFrame(btn_frame, width=2, height=30, fg_color=Colors.SECONDARY)
        separator.pack(side="left", padx=15)

        # 导出按钮
        self.btn_export = ctk.CTkButton(
            btn_frame,
            text="导出",
            width=80,
            fg_color=Colors.SECONDARY,
            command=self._show_export_menu
        )
        self.btn_export.pack(side="left", padx=(0, 10))

        # 对比按钮
        self.btn_compare = ctk.CTkButton(
            btn_frame,
            text="对比",
            width=80,
            fg_color=Colors.SECONDARY,
            command=self._compare_file
        )
        self.btn_compare.pack(side="left")

        # 右侧：修改状态指示
        self.modified_label = ctk.CTkLabel(
            toolbar,
            text="",
            font=("Arial", 11),
            text_color=Colors.MODIFIED
        )
        self.modified_label.pack(side="right", padx=15)

    def _create_main_area(self):
        """创建主区域（选项卡）"""
        self.tabview = ctk.CTkTabview(self, fg_color="transparent")
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=10, pady=(5, 0))

        # 创建选项卡
        self.tab_overview = self.tabview.add("概览")
        self.tab_details = self.tabview.add("详细参数")
        self.tab_timing = self.tabview.add("时序")
        self.tab_xmp = self.tabview.add("XMP")
        self.tab_hex = self.tabview.add("十六进制")
        self.tab_log = self.tabview.add("日志")

        # 配置选项卡
        for tab in [self.tab_overview, self.tab_details, self.tab_timing,
                    self.tab_xmp, self.tab_hex, self.tab_log]:
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)

        # 创建选项卡内容
        self.overview_tab = OverviewTab(self.tab_overview, self.data_model)
        self.overview_tab.grid(row=0, column=0, sticky="nsew")

        self.details_tab = DetailsTab(self.tab_details, self.data_model)
        self.details_tab.grid(row=0, column=0, sticky="nsew")

        self.timing_tab = TimingTab(self.tab_timing, self.data_model)
        self.timing_tab.grid(row=0, column=0, sticky="nsew")

        self.xmp_tab = XMPTab(self.tab_xmp, self.data_model)
        self.xmp_tab.grid(row=0, column=0, sticky="nsew")

        self.hex_editor_tab = HexEditorTab(self.tab_hex, self.data_model)
        self.hex_editor_tab.grid(row=0, column=0, sticky="nsew")

        self.log_tab = LogTab(self.tab_log)
        self.log_tab.grid(row=0, column=0, sticky="nsew")

    def _create_statusbar(self):
        """创建状态栏"""
        statusbar = ctk.CTkFrame(self, height=35, fg_color=Colors.CARD_BG)
        statusbar.grid(row=2, column=0, sticky="ew")

        # 进度条
        self.progress = ctk.CTkProgressBar(statusbar, width=200, height=8)
        self.progress.pack(side="left", padx=15, pady=10)
        self.progress.set(0)

        # 状态文本
        self.status_label = ctk.CTkLabel(
            statusbar,
            text="就绪",
            font=("Arial", 11),
            text_color=Colors.TEXT_SECONDARY
        )
        self.status_label.pack(side="left", padx=10)

        # 右侧信息
        self.info_label = ctk.CTkLabel(
            statusbar,
            text="",
            font=("Arial", 11),
            text_color=Colors.TEXT_SECONDARY
        )
        self.info_label.pack(side="right", padx=15)

    def _on_data_changed(self, event: DataChangeEvent):
        """数据变更回调"""
        if self.data_model.is_modified:
            count = self.data_model.modified_count
            self.modified_label.configure(text=f"已修改 {count} 字节")
            self.btn_write.configure(state="normal")
        else:
            self.modified_label.configure(text="")

    def _set_status(self, text: str):
        """设置状态文本"""
        self.status_label.configure(text=text)

    def _set_buttons_state(self, enabled: bool):
        """设置按钮状态"""
        state = "normal" if enabled else "disabled"
        self.btn_read.configure(state=state)
        self.btn_load.configure(state=state)
        self.btn_save.configure(state=state)
        self.btn_export.configure(state=state)
        self.btn_compare.configure(state=state)

        if enabled and self.data_model.has_data:
            self.btn_write.configure(state="normal")
        else:
            self.btn_write.configure(state="disabled")

    def _log(self, message: str, level: str = "info"):
        """记录日志"""
        if level == "info":
            self.log_tab.log_info(message)
        elif level == "success":
            self.log_tab.log_success(message)
        elif level == "warning":
            self.log_tab.log_warning(message)
        elif level == "error":
            self.log_tab.log_error(message)

    # ==================== 操作方法 ====================

    def _start_read(self):
        """开始读取"""
        self._set_buttons_state(False)
        self._set_status("正在连接...")
        self._log("开始读取 SPD 数据...")
        threading.Thread(target=self._run_read, daemon=True).start()

    def _run_read(self):
        """执行读取（后台线程）"""
        try:
            if not self.driver.connect():
                self._log("连接失败，请检查设备", "error")
                self._set_status("连接失败")
                self._set_buttons_state(True)
                return

            self._log("设备已连接")
            self._set_status("正在读取...")

            data = self.driver.read_spd(
                progress_callback=lambda p: self.progress.set(p),
                log_callback=lambda msg: self._log(msg)
            )

            self.driver.disconnect()

            if data:
                self.data_model.load_from_list(data, is_from_device=True)
                self._log("读取完成", "success")

                # 解析并显示信息
                parser = DDR4Parser(data)
                info = parser.to_dict()
                if "error" not in info:
                    self._log(f"检测到: {info.get('manufacturer', 'Unknown')} {info.get('part_number', '')}")
                    self._log(f"容量: {info.get('capacity', '-')}, 速度: {info.get('speed_grade', '-')} MT/s")

                # 自动备份
                backup_path = f"backup_spd_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bin"
                self.data_model.save_to_file(backup_path)
                self._log(f"已自动备份到: {backup_path}")

                self._set_status("读取完成")
                self.info_label.configure(text=f"{info.get('manufacturer', '')} {info.get('capacity', '')}")
            else:
                self._log("读取失败", "error")
                self._set_status("读取失败")

        except Exception as e:
            self._log(f"读取出错: {str(e)}", "error")
            self._set_status("读取出错")
        finally:
            self._set_buttons_state(True)
            self.progress.set(0)

    def _load_file(self):
        """加载文件"""
        path = filedialog.askopenfilename(
            filetypes=[
                ("SPD Binary", "*.bin"),
                ("All files", "*.*")
            ]
        )

        if path:
            if self.data_model.load_from_file(path):
                self._log(f"已加载文件: {os.path.basename(path)}", "success")

                parser = DDR4Parser(self.data_model.data)
                info = parser.to_dict()
                if "error" not in info:
                    self._log(f"检测到: {info.get('manufacturer', 'Unknown')} {info.get('part_number', '')}")

                self._set_status("文件已加载")
                self.info_label.configure(text=os.path.basename(path))
                self.btn_write.configure(state="normal")
            else:
                self._log("加载失败：文件大小必须是 512 字节", "error")
                messagebox.showerror("错误", "文件大小必须是 512 字节 (DDR4 SPD)")

    def _save_file(self):
        """保存文件"""
        if not self.data_model.has_data:
            messagebox.showwarning("警告", "没有可保存的数据")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".bin",
            filetypes=[
                ("SPD Binary", "*.bin"),
                ("All files", "*.*")
            ],
            initialfilename="spd_data.bin"
        )

        if path:
            if self.data_model.save_to_file(path):
                self._log(f"已保存到: {path}", "success")
                self._set_status("已保存")
            else:
                self._log("保存失败", "error")

    def _start_write(self):
        """开始写入"""
        if not self.data_model.has_data:
            return

        # 二次确认
        result = messagebox.askyesno(
            "危险操作",
            "确定要写入 SPD 吗？\n\n"
            "警告：\n"
            "• 写入错误的数据可能导致电脑无法开机！\n"
            "• 写入过程中严禁断电或拔线！\n"
            "• 请确保已备份原始数据。\n\n"
            "是否继续？"
        )

        if not result:
            return

        self._set_buttons_state(False)
        self._set_status("正在写入...")
        self._log("开始写入 SPD 数据...", "warning")
        threading.Thread(target=self._run_write, daemon=True).start()

    def _run_write(self):
        """执行写入（后台线程）"""
        try:
            if not self.driver.connect():
                self._log("连接失败", "error")
                self._set_status("连接失败")
                self._set_buttons_state(True)
                return

            self._log("设备已连接，开始写入...")

            success = self.driver.write_spd(
                self.data_model.data,
                progress_callback=lambda p: self.progress.set(p),
                log_callback=lambda msg: self._log(msg)
            )

            self.driver.disconnect()

            if success:
                self._log("写入成功！请重启电脑。", "success")
                self._set_status("写入成功")
                messagebox.showinfo(
                    "成功",
                    "SPD 数据写入成功！\n\n"
                    "请将内存条安装到电脑上并重启。\n"
                    "如果启用了 XMP，请在 BIOS 中开启。"
                )
            else:
                self._log("写入失败", "error")
                self._set_status("写入失败")
                messagebox.showerror("失败", "写入过程中出现错误，请重试。")

        except Exception as e:
            self._log(f"写入出错: {str(e)}", "error")
            self._set_status("写入出错")
        finally:
            self._set_buttons_state(True)
            self.progress.set(0)

    def _show_export_menu(self):
        """显示导出菜单"""
        if not self.data_model.has_data:
            messagebox.showwarning("警告", "没有可导出的数据")
            return

        # 创建菜单窗口
        menu = ExportMenu(self, self.data_model, self._log)

    def _compare_file(self):
        """对比文件"""
        if not self.data_model.has_data:
            messagebox.showwarning("警告", "请先加载或读取数据")
            return

        path = filedialog.askopenfilename(
            title="选择要对比的文件",
            filetypes=[
                ("SPD Binary", "*.bin"),
                ("All files", "*.*")
            ]
        )

        if not path:
            return

        try:
            with open(path, "rb") as f:
                compare_data = list(f.read())

            if len(compare_data) != SPD_SIZE:
                messagebox.showerror("错误", "对比文件大小必须是 512 字节")
                return

            differences = self.data_model.compare_with(compare_data)

            if not differences:
                self._log("对比结果：两份数据完全相同", "success")
                messagebox.showinfo("对比结果", "两份数据完全相同")
            else:
                self._log(f"对比结果：发现 {len(differences)} 处差异", "warning")

                # 显示详细差异
                diff_window = CompareResultWindow(self, differences, os.path.basename(path))

        except Exception as e:
            self._log(f"对比失败: {str(e)}", "error")
            messagebox.showerror("错误", f"对比失败: {str(e)}")


class ExportMenu(ctk.CTkToplevel):
    """导出菜单窗口"""

    def __init__(self, parent, data_model: SPDDataModel, log_callback):
        super().__init__(parent)

        self.title("导出")
        self.geometry("300x200")
        self.resizable(False, False)

        self.data_model = data_model
        self.log_callback = log_callback

        self.transient(parent)
        self.grab_set()

        self._setup_ui()

    def _setup_ui(self):
        """设置UI"""
        ctk.CTkLabel(
            self,
            text="选择导出格式",
            font=("Arial", 14, "bold")
        ).pack(pady=(20, 15))

        ctk.CTkButton(
            self,
            text="导出为 BIN (二进制)",
            width=200,
            command=self._export_bin
        ).pack(pady=5)

        ctk.CTkButton(
            self,
            text="导出为 TXT (文本报告)",
            width=200,
            command=self._export_txt
        ).pack(pady=5)

        ctk.CTkButton(
            self,
            text="导出为 JSON",
            width=200,
            command=self._export_json
        ).pack(pady=5)

    def _export_bin(self):
        """导出为二进制"""
        path = filedialog.asksaveasfilename(
            defaultextension=".bin",
            filetypes=[("Binary", "*.bin")],
            initialfilename="spd_export.bin"
        )
        if path:
            self.data_model.save_to_file(path)
            self.log_callback(f"已导出到: {path}", "success")
            self.destroy()

    def _export_txt(self):
        """导出为文本"""
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text", "*.txt")],
            initialfilename="spd_report.txt"
        )
        if path:
            content = self.data_model.export_to_text()
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            self.log_callback(f"已导出到: {path}", "success")
            self.destroy()

    def _export_json(self):
        """导出为 JSON"""
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialfilename="spd_data.json"
        )
        if path:
            content = self.data_model.export_to_json()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(content, f, indent=2, ensure_ascii=False)
            self.log_callback(f"已导出到: {path}", "success")
            self.destroy()


class CompareResultWindow(ctk.CTkToplevel):
    """对比结果窗口"""

    def __init__(self, parent, differences: dict, compare_filename: str):
        super().__init__(parent)

        self.title("对比结果")
        self.geometry("500x400")

        self.differences = differences
        self.compare_filename = compare_filename

        self._setup_ui()

    def _setup_ui(self):
        """设置UI"""
        # 头部信息
        header = ctk.CTkFrame(self, fg_color=Colors.CARD_BG)
        header.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            header,
            text=f"与 {self.compare_filename} 对比",
            font=("Arial", 12, "bold")
        ).pack(anchor="w", padx=15, pady=(10, 5))

        ctk.CTkLabel(
            header,
            text=f"发现 {len(self.differences)} 处差异",
            font=("Arial", 11),
            text_color=Colors.WARNING
        ).pack(anchor="w", padx=15, pady=(0, 10))

        # 差异列表
        scroll_frame = ctk.CTkScrollableFrame(self)
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # 表头
        header_frame = ctk.CTkFrame(scroll_frame, fg_color=Colors.SECONDARY)
        header_frame.pack(fill="x", pady=(0, 5))

        for col, text in enumerate(["偏移", "当前值", "对比值"]):
            ctk.CTkLabel(
                header_frame,
                text=text,
                font=("Arial", 11, "bold"),
                width=120
            ).grid(row=0, column=col, padx=10, pady=5)

        # 差异行
        for offset, (current, compare) in sorted(self.differences.items()):
            row_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
            row_frame.pack(fill="x")

            ctk.CTkLabel(
                row_frame,
                text=f"0x{offset:03X}",
                font=("Consolas", 11),
                width=120
            ).grid(row=0, column=0, padx=10, pady=2)

            ctk.CTkLabel(
                row_frame,
                text=f"0x{current:02X}",
                font=("Consolas", 11),
                text_color=Colors.HIGHLIGHT,
                width=120
            ).grid(row=0, column=1, padx=10, pady=2)

            ctk.CTkLabel(
                row_frame,
                text=f"0x{compare:02X}",
                font=("Consolas", 11),
                text_color=Colors.WARNING,
                width=120
            ).grid(row=0, column=2, padx=10, pady=2)
