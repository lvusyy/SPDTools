"""
十六进制视图/编辑器组件
"""

import customtkinter as ctk
from tkinter import font as tkfont
import tkinter as tk
from typing import Optional, Callable, List, Set

from ...utils.constants import Colors, SPD_SIZE


class HexView(ctk.CTkFrame):
    """十六进制视图/编辑器组件"""

    BYTES_PER_ROW = 16
    ROWS_VISIBLE = 20

    def __init__(
        self,
        master,
        data: Optional[List[int]] = None,
        editable: bool = True,
        on_byte_changed: Optional[Callable[[int, int], None]] = None,
        modified_bytes: Optional[Set[int]] = None,
        **kwargs
    ):
        super().__init__(master, fg_color=Colors.CARD_BG, **kwargs)

        self._data = data if data else [0] * SPD_SIZE
        self.editable = editable
        self.on_byte_changed = on_byte_changed
        self._modified_bytes = modified_bytes if modified_bytes else set()
        self._selected_offset = -1
        self._selection_start = -1
        self._selection_end = -1

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)  # 主显示区域在 row 1

        self._setup_ui()
        self._update_display()

    def _setup_ui(self):
        """设置UI"""
        # 工具栏
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.grid(row=0, column=0, columnspan=3, sticky="ew", padx=10, pady=(10, 5))

        # 跳转输入
        ctk.CTkLabel(toolbar, text="跳转到:", font=("Arial", 11)).pack(side="left")
        self.goto_entry = ctk.CTkEntry(toolbar, width=80, placeholder_text="0x000")
        self.goto_entry.pack(side="left", padx=(5, 0))
        self.goto_entry.bind("<Return>", self._on_goto)

        ctk.CTkButton(
            toolbar,
            text="Go",
            width=40,
            command=self._on_goto
        ).pack(side="left", padx=(5, 20))

        # 当前选择信息
        self.selection_label = ctk.CTkLabel(
            toolbar,
            text="选择: -",
            font=("Arial", 11),
            text_color=Colors.TEXT_SECONDARY
        )
        self.selection_label.pack(side="left")

        # 修改计数
        self.modified_label = ctk.CTkLabel(
            toolbar,
            text="",
            font=("Arial", 11),
            text_color=Colors.MODIFIED
        )
        self.modified_label.pack(side="right")

        # 主显示区域使用 Canvas + Scrollbar
        display_frame = ctk.CTkFrame(self, fg_color="transparent")
        display_frame.grid(row=1, column=0, columnspan=3, sticky="nsew", padx=10, pady=(0, 10))
        display_frame.grid_columnconfigure(0, weight=1)
        display_frame.grid_rowconfigure(0, weight=1)

        # 使用 Text 组件实现
        self.hex_text = ctk.CTkTextbox(
            display_frame,
            font=("Consolas", 11),
            fg_color="#1e1e1e",
            text_color=Colors.TEXT,
            wrap="none",
            state="normal"
        )
        self.hex_text.grid(row=0, column=0, sticky="nsew")

        # 绑定事件
        self.hex_text.bind("<Button-1>", self._on_click)
        self.hex_text.bind("<B1-Motion>", self._on_drag)
        self.hex_text.bind("<ButtonRelease-1>", self._on_release)
        self.hex_text.bind("<Double-Button-1>", self._on_double_click)
        self.hex_text.bind("<Button-3>", self._on_right_click)
        self.hex_text.bind("<Key>", self._on_key)

        # 创建右键菜单
        self._create_context_menu()

        # 配置标签样式
        # 注意: CTkTextbox 的 tag_config 不支持 font 选项
        self.hex_text.tag_config("address", foreground="#6A9955")
        self.hex_text.tag_config("hex", foreground=Colors.TEXT)
        self.hex_text.tag_config("ascii", foreground="#CE9178")
        self.hex_text.tag_config("modified", foreground=Colors.MODIFIED)
        self.hex_text.tag_config("selected", background=Colors.PRIMARY)
        self.hex_text.tag_config("range_selected", background="#264F78")
        self.hex_text.tag_config("separator", foreground=Colors.TEXT_SECONDARY)

    def _create_context_menu(self):
        """创建右键上下文菜单"""
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="复制十六进制", command=self._copy_hex)
        self.context_menu.add_command(label="复制ASCII", command=self._copy_ascii)
        self.context_menu.add_command(label="复制十六进制 + ASCII", command=self._copy_hex_and_ascii)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="复制为C数组", command=self._copy_as_c_array)
        self.context_menu.add_command(label="复制为Python列表", command=self._copy_as_python_list)

    def _update_display(self):
        """更新显示内容"""
        self.hex_text.configure(state="normal")
        self.hex_text.delete("1.0", "end")

        for row in range(0, SPD_SIZE, self.BYTES_PER_ROW):
            # 地址
            address = f"{row:03X}  "
            self.hex_text.insert("end", address, "address")

            # 十六进制数据
            hex_parts = []
            for i in range(self.BYTES_PER_ROW):
                offset = row + i
                if offset < len(self._data):
                    byte_val = self._data[offset]
                    hex_str = f"{byte_val:02X}"

                    # 检查是否被修改
                    if offset in self._modified_bytes:
                        self.hex_text.insert("end", hex_str, "modified")
                    else:
                        self.hex_text.insert("end", hex_str, "hex")

                    # 每8字节添加额外空格
                    if i == 7:
                        self.hex_text.insert("end", "  ", "separator")
                    elif i < self.BYTES_PER_ROW - 1:
                        self.hex_text.insert("end", " ", "separator")
                else:
                    self.hex_text.insert("end", "   ", "hex")

            # ASCII 区域
            self.hex_text.insert("end", "  |", "separator")
            for i in range(self.BYTES_PER_ROW):
                offset = row + i
                if offset < len(self._data):
                    byte_val = self._data[offset]
                    if 32 <= byte_val < 127:
                        char = chr(byte_val)
                    else:
                        char = "."
                    self.hex_text.insert("end", char, "ascii")
            self.hex_text.insert("end", "|\n", "separator")

        # 更新修改计数
        if self._modified_bytes:
            self.modified_label.configure(text=f"已修改: {len(self._modified_bytes)} 字节")
        else:
            self.modified_label.configure(text="")

        if not self.editable:
            self.hex_text.configure(state="disabled")

    def _on_click(self, event):
        """点击事件 - 开始选择"""
        offset = self._get_offset_from_position(event.x, event.y)
        if offset >= 0:
            self._selection_start = offset
            self._selection_end = offset
            self._select_byte(offset)

    def _on_drag(self, event):
        """拖拽事件 - 扩展选择范围"""
        offset = self._get_offset_from_position(event.x, event.y)
        if offset >= 0 and self._selection_start >= 0:
            self._selection_end = offset
            self._highlight_range_selection()

    def _on_release(self, event):
        """释放鼠标 - 完成选择"""
        if self._selection_start >= 0 and self._selection_end >= 0:
            # 确保 start <= end
            if self._selection_start > self._selection_end:
                self._selection_start, self._selection_end = self._selection_end, self._selection_start
            self._update_selection_label()

    def _on_right_click(self, event):
        """右键点击 - 显示上下文菜单"""
        # 如果没有选择范围，选择点击的字节
        offset = self._get_offset_from_position(event.x, event.y)
        if offset >= 0:
            if self._selection_start < 0 or self._selection_end < 0:
                self._selection_start = offset
                self._selection_end = offset
                self._select_byte(offset)
            elif offset < min(self._selection_start, self._selection_end) or offset > max(self._selection_start, self._selection_end):
                # 点击在选择范围外，重新选择
                self._selection_start = offset
                self._selection_end = offset
                self._select_byte(offset)

        # 显示右键菜单
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def _get_offset_from_position(self, x: int, y: int) -> int:
        """从屏幕坐标获取字节偏移量"""
        index = self.hex_text.index(f"@{x},{y}")
        line, col = map(int, index.split("."))

        # 格式: "XXX  HH HH HH HH HH HH HH HH  HH HH HH HH HH HH HH HH  |................|"
        # 地址占 5 字符，每个十六进制占 3 字符（含空格），中间额外空格 2 字符
        if col >= 5 and col < 53:  # 十六进制区域
            adjusted_col = col - 5
            if adjusted_col >= 24:  # 跳过中间分隔
                adjusted_col -= 2
            byte_index = adjusted_col // 3
            if byte_index < self.BYTES_PER_ROW:
                offset = (line - 1) * self.BYTES_PER_ROW + byte_index
                if offset < len(self._data):
                    return offset
        elif col >= 55 and col < 71:  # ASCII 区域
            ascii_col = col - 55
            if ascii_col < self.BYTES_PER_ROW:
                offset = (line - 1) * self.BYTES_PER_ROW + ascii_col
                if offset < len(self._data):
                    return offset
        return -1

    def _highlight_range_selection(self):
        """高亮范围选择"""
        self.hex_text.tag_remove("range_selected", "1.0", "end")
        self.hex_text.tag_remove("selected", "1.0", "end")

        if self._selection_start < 0 or self._selection_end < 0:
            return

        start = min(self._selection_start, self._selection_end)
        end = max(self._selection_start, self._selection_end)

        for offset in range(start, end + 1):
            row = offset // self.BYTES_PER_ROW
            col = offset % self.BYTES_PER_ROW

            # 高亮十六进制区域
            text_col = 5 + col * 3
            if col >= 8:
                text_col += 2
            hex_start = f"{row + 1}.{text_col}"
            hex_end = f"{row + 1}.{text_col + 2}"
            self.hex_text.tag_add("range_selected", hex_start, hex_end)

            # 高亮 ASCII 区域
            ascii_col = 55 + col
            ascii_start = f"{row + 1}.{ascii_col}"
            ascii_end = f"{row + 1}.{ascii_col + 1}"
            self.hex_text.tag_add("range_selected", ascii_start, ascii_end)

        self._update_selection_label()

    def _update_selection_label(self):
        """更新选择信息标签"""
        if self._selection_start >= 0 and self._selection_end >= 0:
            start = min(self._selection_start, self._selection_end)
            end = max(self._selection_start, self._selection_end)
            count = end - start + 1
            if count == 1:
                self.selection_label.configure(
                    text=f"选择: 0x{start:03X} = 0x{self._data[start]:02X} ({self._data[start]})"
                )
            else:
                self.selection_label.configure(
                    text=f"选择: 0x{start:03X} - 0x{end:03X} ({count} 字节)"
                )

    def _get_selected_bytes(self) -> List[int]:
        """获取选中的字节"""
        if self._selection_start < 0 or self._selection_end < 0:
            if self._selected_offset >= 0:
                return [self._data[self._selected_offset]]
            return []

        start = min(self._selection_start, self._selection_end)
        end = max(self._selection_start, self._selection_end)
        return self._data[start:end + 1]

    def _copy_hex(self):
        """复制为十六进制字符串"""
        bytes_data = self._get_selected_bytes()
        if bytes_data:
            hex_str = " ".join(f"{b:02X}" for b in bytes_data)
            self._copy_to_clipboard(hex_str)
            print(f"[DEBUG HexView] Copied hex: {hex_str}")

    def _copy_ascii(self):
        """复制为ASCII字符串"""
        bytes_data = self._get_selected_bytes()
        if bytes_data:
            ascii_str = "".join(chr(b) if 32 <= b < 127 else "." for b in bytes_data)
            self._copy_to_clipboard(ascii_str)
            print(f"[DEBUG HexView] Copied ASCII: {ascii_str}")

    def _copy_hex_and_ascii(self):
        """复制十六进制和ASCII"""
        bytes_data = self._get_selected_bytes()
        if bytes_data:
            hex_str = " ".join(f"{b:02X}" for b in bytes_data)
            ascii_str = "".join(chr(b) if 32 <= b < 127 else "." for b in bytes_data)
            combined = f"{hex_str}  |{ascii_str}|"
            self._copy_to_clipboard(combined)
            print(f"[DEBUG HexView] Copied hex+ASCII: {combined}")

    def _copy_as_c_array(self):
        """复制为C数组格式"""
        bytes_data = self._get_selected_bytes()
        if bytes_data:
            c_array = "{ " + ", ".join(f"0x{b:02X}" for b in bytes_data) + " }"
            self._copy_to_clipboard(c_array)
            print(f"[DEBUG HexView] Copied C array: {c_array}")

    def _copy_as_python_list(self):
        """复制为Python列表格式"""
        bytes_data = self._get_selected_bytes()
        if bytes_data:
            py_list = "[" + ", ".join(f"0x{b:02X}" for b in bytes_data) + "]"
            self._copy_to_clipboard(py_list)
            print(f"[DEBUG HexView] Copied Python list: {py_list}")

    def _copy_to_clipboard(self, text: str):
        """复制到剪贴板"""
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()

    def _on_double_click(self, event):
        """双击编辑"""
        if self.editable and self._selected_offset >= 0:
            self._edit_byte(self._selected_offset)

    def _on_key(self, event):
        """键盘事件"""
        if not self.editable:
            return "break"

        if self._selected_offset < 0:
            return "break"

        # 处理十六进制输入
        char = event.char.upper() if event.char else ""
        if char and char in "0123456789ABCDEF":
            try:
                current_val = self._data[self._selected_offset]
                # 左移4位并加入新值
                new_val = ((current_val << 4) | int(char, 16)) & 0xFF
                self._set_byte(self._selected_offset, new_val)
            except (ValueError, IndexError):
                pass
            return "break"

        # 导航键
        if event.keysym == "Right":
            self._select_byte(min(self._selected_offset + 1, len(self._data) - 1))
        elif event.keysym == "Left":
            self._select_byte(max(self._selected_offset - 1, 0))
        elif event.keysym == "Down":
            new_offset = self._selected_offset + self.BYTES_PER_ROW
            if new_offset < len(self._data):
                self._select_byte(new_offset)
        elif event.keysym == "Up":
            new_offset = self._selected_offset - self.BYTES_PER_ROW
            if new_offset >= 0:
                self._select_byte(new_offset)

        return "break"

    def _select_byte(self, offset: int):
        """选择字节"""
        self._selected_offset = offset
        self.selection_label.configure(
            text=f"选择: 0x{offset:03X} = 0x{self._data[offset]:02X} ({self._data[offset]})"
        )
        self._update_display()
        self._highlight_selection()

    def _highlight_selection(self):
        """高亮选中的字节"""
        if self._selected_offset < 0:
            return

        self.hex_text.tag_remove("selected", "1.0", "end")
        self.hex_text.tag_remove("range_selected", "1.0", "end")

        row = self._selected_offset // self.BYTES_PER_ROW
        col = self._selected_offset % self.BYTES_PER_ROW

        # 高亮十六进制区域
        text_col = 5 + col * 3
        if col >= 8:
            text_col += 2  # 跳过中间分隔
        hex_start = f"{row + 1}.{text_col}"
        hex_end = f"{row + 1}.{text_col + 2}"
        self.hex_text.tag_add("selected", hex_start, hex_end)

        # 高亮 ASCII 区域
        ascii_col = 55 + col
        ascii_start = f"{row + 1}.{ascii_col}"
        ascii_end = f"{row + 1}.{ascii_col + 1}"
        self.hex_text.tag_add("selected", ascii_start, ascii_end)

    def _edit_byte(self, offset: int):
        """编辑字节（弹出对话框）"""
        dialog = ByteEditDialog(
            self,
            offset=offset,
            current_value=self._data[offset],
            on_save=lambda v: self._set_byte(offset, v)
        )

    def _set_byte(self, offset: int, value: int):
        """设置字节值"""
        if 0 <= value <= 255:
            old_value = self._data[offset]
            self._data[offset] = value
            self._modified_bytes.add(offset)
            self._update_display()
            self._highlight_selection()

            if self.on_byte_changed:
                self.on_byte_changed(offset, value)

    def _on_goto(self, event=None):
        """跳转到指定偏移"""
        try:
            text = self.goto_entry.get().strip()
            if text.startswith("0x") or text.startswith("0X"):
                offset = int(text, 16)
            else:
                offset = int(text)

            if 0 <= offset < len(self._data):
                self._select_byte(offset)
                # 滚动到可见
                row = offset // self.BYTES_PER_ROW
                self.hex_text.see(f"{row + 1}.0")
        except ValueError:
            pass

    def set_data(self, data: List[int], modified_bytes: Optional[Set[int]] = None):
        """设置数据"""
        self._data = data.copy() if data else [0] * SPD_SIZE
        self._modified_bytes = modified_bytes.copy() if modified_bytes else set()
        self._selected_offset = -1
        self._update_display()

    def get_data(self) -> List[int]:
        """获取数据"""
        return self._data.copy()

    def set_modified_bytes(self, modified_bytes: Set[int]):
        """设置修改的字节集合"""
        self._modified_bytes = modified_bytes.copy()
        self._update_display()

    def highlight_offset(self, offset: int):
        """高亮指定偏移"""
        self._select_byte(offset)
        row = offset // self.BYTES_PER_ROW
        self.hex_text.see(f"{row + 1}.0")


class ByteEditDialog(ctk.CTkToplevel):
    """字节编辑对话框"""

    def __init__(self, parent, offset: int, current_value: int, on_save: Callable[[int], None]):
        super().__init__(parent)

        self.title(f"编辑字节 0x{offset:03X}")
        self.geometry("300x320")
        self.resizable(False, False)

        self.offset = offset
        self.current_value = current_value
        self.on_save = on_save

        self.transient(parent)
        self.grab_set()

        self._setup_ui()

    def _setup_ui(self):
        """设置UI"""
        # 当前值显示
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.pack(fill="x", padx=20, pady=(20, 10))

        ctk.CTkLabel(
            info_frame,
            text=f"偏移: 0x{self.offset:03X} ({self.offset})",
            font=("Arial", 12)
        ).pack(anchor="w")

        ctk.CTkLabel(
            info_frame,
            text=f"当前值: 0x{self.current_value:02X} ({self.current_value})",
            font=("Arial", 12)
        ).pack(anchor="w")

        # 输入框
        input_frame = ctk.CTkFrame(self, fg_color="transparent")
        input_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(input_frame, text="新值 (十六进制):").pack(anchor="w")
        self.hex_entry = ctk.CTkEntry(input_frame, placeholder_text="00-FF")
        self.hex_entry.pack(fill="x", pady=(5, 0))
        self.hex_entry.insert(0, f"{self.current_value:02X}")
        self.hex_entry.select_range(0, "end")
        self.hex_entry.focus()

        ctk.CTkLabel(input_frame, text="或 (十进制):").pack(anchor="w", pady=(10, 0))
        self.dec_entry = ctk.CTkEntry(input_frame, placeholder_text="0-255")
        self.dec_entry.pack(fill="x", pady=(5, 0))
        self.dec_entry.insert(0, str(self.current_value))

        # 联动
        self.hex_entry.bind("<KeyRelease>", self._on_hex_change)
        self.dec_entry.bind("<KeyRelease>", self._on_dec_change)
        self.hex_entry.bind("<Return>", self._on_save)
        self.dec_entry.bind("<Return>", self._on_save)

        # 按钮
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(15, 20))

        ctk.CTkButton(
            btn_frame,
            text="取消",
            width=100,
            height=32,
            fg_color=Colors.SECONDARY,
            command=self.destroy
        ).pack(side="left", expand=True, padx=(0, 10))

        ctk.CTkButton(
            btn_frame,
            text="保存",
            width=100,
            height=32,
            command=self._on_save
        ).pack(side="right", expand=True, padx=(10, 0))

    def _on_hex_change(self, event):
        """十六进制输入变化"""
        try:
            value = int(self.hex_entry.get(), 16)
            if 0 <= value <= 255:
                self.dec_entry.delete(0, "end")
                self.dec_entry.insert(0, str(value))
        except ValueError:
            pass

    def _on_dec_change(self, event):
        """十进制输入变化"""
        try:
            value = int(self.dec_entry.get())
            if 0 <= value <= 255:
                self.hex_entry.delete(0, "end")
                self.hex_entry.insert(0, f"{value:02X}")
        except ValueError:
            pass

    def _on_save(self, event=None):
        """保存"""
        try:
            value = int(self.hex_entry.get(), 16)
            if 0 <= value <= 255:
                self.on_save(value)
                self.destroy()
        except ValueError:
            pass
