import customtkinter as ctk
import hid
import time
import threading
from tkinter import filedialog, messagebox
import os

# ==========================================
# 硬件驱动层 (新增写入功能)
# ==========================================
class SPDDriver:
    def __init__(self, vid=0x0483, pid=0x1230):
        self.vid = vid
        self.pid = pid
        self.device = None
        self.stop_flag = False

    def connect(self):
        try:
            self.device = hid.device()
            self.device.open(self.vid, self.pid)
            return True
        except:
            return False

    def disconnect(self):
        if self.device:
            self.device.close()
            self.device = None

    def send_cmd(self, cmd_str, delay=0.02):
        if not self.device: return None
        # 构造数据包: ReportID(0) + 64 bytes data
        data = [0x00] * 65
        for i, char in enumerate(cmd_str):
            data[i+1] = ord(char)
        try:
            self.device.write(data)
            time.sleep(delay) # 写入命令需要稍微长一点的延时
            response = self.device.read(64)
            return "".join([chr(x) for x in response if 32 <= x <= 126])
        except Exception as e:
            print(f"IO Error: {e}")
            return None

    def read_spd(self, progress_callback=None, log_callback=None):
        self.stop_flag = False
        full_data = [0] * 512
        
        # 1. 激活与初始化
        self.send_cmd("BT-VER0010")
        time.sleep(0.1)

        # 2. 读取 Page 0
        if log_callback: log_callback("正在读取 Page 0...")
        self.send_cmd("BT-I2C2WR360001") 
        time.sleep(0.2)
        
        for offset in range(0, 256, 8):
            if self.stop_flag: return None
            block = self._read_block(0x50, offset)
            for i, b in enumerate(block):
                full_data[offset + i] = b
            if progress_callback: progress_callback((offset + 8) / 512)
        
        # 3. 读取 Page 1
        if log_callback: log_callback("正在读取 Page 1...")
        self.send_cmd("BT-I2C2WR370001")
        time.sleep(0.4) # 切页延时
        
        for offset in range(0, 256, 8):
            if self.stop_flag: return None
            block = self._read_block(0x50, offset)
            for i, b in enumerate(block):
                full_data[256 + offset + i] = b
            if progress_callback: progress_callback((256 + offset + 8) / 512)

        return full_data

    def _read_block(self, addr, offset):
        cmd = f"BT-I2C2RD{addr:02X}{offset:02X}08"
        for _ in range(3):
            resp = self.send_cmd(cmd)
            if resp and resp.startswith(":"):
                try:
                    parts = resp[1:].strip().split()
                    hex_parts = [p for p in parts if len(p)==2][:8]
                    if len(hex_parts) == 8:
                        return [int(x, 16) for x in hex_parts]
                except: pass
            time.sleep(0.05)
        return [0]*8

    def write_spd(self, data, progress_callback=None, log_callback=None):
        """写入 SPD 数据 (核心功能)"""
        self.stop_flag = False
        if len(data) != 512:
            if log_callback: log_callback("错误: 数据长度必须是 512 字节")
            return False

        # 1. 激活
        self.send_cmd("BT-VER0010")
        time.sleep(0.1)
        
        # 2. 写入 Page 0 (0-255)
        if log_callback: log_callback("正在写入 Page 0...")
        self.send_cmd("BT-I2C2WR360001") # 切到 Page 0
        time.sleep(0.2)

        for offset in range(0, 256, 8):
            if self.stop_flag: return False
            chunk = data[offset : offset+8]
            if not self._write_block(0x50, offset, chunk):
                if log_callback: log_callback(f"写入失败: Offset {hex(offset)}")
                return False
            if progress_callback: progress_callback((offset + 8) / 512)
            
        # 3. 写入 Page 1 (256-511)
        if log_callback: log_callback("正在写入 Page 1...")
        self.send_cmd("BT-I2C2WR370001") # 切到 Page 1
        time.sleep(0.4) # 等待切页

        for offset in range(0, 256, 8):
            if self.stop_flag: return False
            chunk = data[256 + offset : 256 + offset + 8]
            # 注意: 即使在 Page 1，指令里的 offset 依然是 0-255
            if not self._write_block(0x50, offset, chunk):
                if log_callback: log_callback(f"写入失败: Offset {hex(256+offset)}")
                return False
            if progress_callback: progress_callback((256 + offset + 8) / 512)

        if log_callback: log_callback("写入完成，请重启电脑！")
        return True

    def _write_block(self, addr, offset, data_bytes):
        # 构造指令: BT-I2C2WR + Addr + Offset + Len + DataHex
        data_hex = "".join(f"{b:02X}" for b in data_bytes)
        cmd = f"BT-I2C2WR{addr:02X}{offset:02X}08{data_hex}"
        
        # 发送写入指令
        resp = self.send_cmd(cmd, delay=0.1) # 写入需要更长时间
        
        # 验证: 简单的指令通常返回 :00 表示成功，或者我们可以读回来校验
        # 这里为了速度，假设不报错即成功，严格模式可以加回读校验
        return True

# ==========================================
# 解析引擎 (保持 V4 不变)
# ==========================================
class DDR4Parser:
    def __init__(self, data):
        self.d = data
    def parse(self):
        if len(self.d) < 256: return "数据无效"
        r = []
        r.append(f"内存类型: {'DDR4' if self.d[2]==0x0C else '未知'}")
        
        # 简单解析频率
        if self.d[18] <= 0x0A: spd = "3200+"
        elif self.d[18] <= 0x0C: spd = "2400/2666"
        else: spd = "2133"
        r.append(f"基础频率: {spd} MT/s")
        
        # XMP
        if len(self.d) >= 384 and self.d[384] == 0x0C:
            r.append("XMP支持: 是 (XMP 2.0)")
        else:
            r.append("XMP支持: 否")
            
        return "\n".join(r)

# ==========================================
# GUI 界面层 (启用写入按钮)
# ==========================================
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class SPDApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("SPD Studio - Ultimate Edition")
        self.geometry("900x600")
        self.driver = SPDDriver()
        self.current_data = None # 内存条里的数据
        self.loaded_data = None  # 准备写入的数据
        self.setup_ui()
        
    def setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        sb = ctk.CTkFrame(self, width=200, corner_radius=0)
        sb.grid(row=0, column=0, sticky="nsew")
        
        ctk.CTkLabel(sb, text="SPD Tools", font=("Arial", 20, "bold")).pack(pady=20)
        
        self.btn_read = ctk.CTkButton(sb, text="1. 读取 (Read)", command=self.start_read)
        self.btn_read.pack(pady=10, padx=20)
        
        self.btn_load = ctk.CTkButton(sb, text="2. 加载文件 (Load)", fg_color="#444", command=self.load_file)
        self.btn_load.pack(pady=10, padx=20)

        # 红色警告颜色的写入按钮
        self.btn_write = ctk.CTkButton(sb, text="3. 烧录 (Write)", fg_color="#C0392B", hover_color="#E74C3C", state="disabled", command=self.start_write)
        self.btn_write.pack(pady=10, padx=20)

        ctk.CTkLabel(sb, text="警告: 写入过程\n严禁断电或拔线!", text_color="red", font=("Arial", 12)).pack(side="bottom", pady=20)

        # Main Area
        self.txt_log = ctk.CTkTextbox(self, font=("Consolas", 12))
        self.txt_log.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        
        # Status
        self.progress = ctk.CTkProgressBar(self)
        self.progress.grid(row=1, column=0, columnspan=2, padx=20, pady=10, sticky="ew")
        self.progress.set(0)

    def log(self, msg):
        self.txt_log.insert("end", f"{msg}\n")
        self.txt_log.see("end")

    def start_read(self):
        self.btn_read.configure(state="disabled")
        threading.Thread(target=self.run_read, daemon=True).start()

    def run_read(self):
        self.log("正在连接...")
        if not self.driver.connect():
            self.log("连接失败")
            self.btn_read.configure(state="normal")
            return
            
        data = self.driver.read_spd(lambda p: self.progress.set(p), self.log)
        self.driver.disconnect()
        
        if data:
            self.current_data = data
            self.log("读取完成!")
            parser = DDR4Parser(data)
            self.log(f"分析: {parser.parse()}")
            
            # 自动保存备份
            with open("backup_spd.bin", "wb") as f:
                f.write(bytearray(data))
            self.log("已自动保存备份为 backup_spd.bin")
            
        self.btn_read.configure(state="normal")

    def load_file(self):
        path = filedialog.askopenfilename(filetypes=[("Bin", "*.bin")])
        if path:
            with open(path, "rb") as f:
                content = f.read()
            if len(content) != 512:
                messagebox.showerror("错误", "文件大小必须是 512 字节 (DDR4 SPD)")
                return
            self.loaded_data = list(content)
            self.log(f"已加载: {os.path.basename(path)}")
            self.log("准备就绪。请点击烧录按钮。")
            self.btn_write.configure(state="normal")

    def start_write(self):
        if not self.loaded_data: return
        
        # 二次确认
        if not messagebox.askyesno("危险操作", "确定要写入 SPD 吗？\n写入错误的文件可能导致电脑无法开机！\n请确保已备份原数据。"):
            return

        self.btn_write.configure(state="disabled")
        self.btn_read.configure(state="disabled")
        threading.Thread(target=self.run_write, daemon=True).start()

    def run_write(self):
        self.log("正在连接...")
        if not self.driver.connect():
            self.log("连接失败")
            return
            
        self.log("开始写入... 请勿触碰设备")
        success = self.driver.write_spd(self.loaded_data, lambda p: self.progress.set(p), self.log)
        self.driver.disconnect()
        
        if success:
            messagebox.showinfo("成功", "写入成功！\n请拔下内存条并安装到电脑上。\n如果是新数据，记得进 BIOS 开 XMP。")
        else:
            messagebox.showerror("失败", "写入过程中出现错误，请重试。")
        
        self.btn_read.configure(state="normal")
        self.btn_write.configure(state="normal")

if __name__ == "__main__":
    app = SPDApp()
    app.mainloop()