import os
import subprocess
import time
import atexit
import gdb  # 確保這個腳本在 gdb 中執行

# 獲取 gdb 原始終端的 TTY 路徑
original_tty = gdb.execute("shell tty", to_string=True).strip()

# 預設只開啟 source 面板
gdb.execute("dashboard -layout source")

# 全局變量用來保存各個終端的 PID 和 TTY
stack_pid, stack_tty = None, None
assembly_pid, assembly_tty = None, None
memory_pid, memory_tty = None, None
expressions_pid, expressions_tty = None, None
history_pid, history_tty = None, None
threads_pid, threads_tty = None, None
registers_pid, registers_tty = None, None
breakpoints_pid, breakpoints_tty = None, None
variables_pid, variables_tty = None, None

# 面板名稱與變數的對應關係
panel_info = {
    "stack": ("stack_tty", "stack_pid"),
    "assembly": ("assembly_tty", "assembly_pid"),
    "memory": ("memory_tty", "memory_pid"),
    "expressions": ("expressions_tty", "expressions_pid"),
    "history": ("history_tty", "history_pid"),
    "threads": ("threads_tty", "threads_pid"),
    "registers": ("registers_tty", "registers_pid"),
    "breakpoints": ("breakpoints_tty", "breakpoints_pid"),
    "variables": ("variables_tty", "variables_pid")
}

def open_terminal_and_get_tty(filepath):
    # 啟動新的 st 終端並將 TTY 編號寫入指定的文件，並保持終端打開
    process = subprocess.Popen(['st', '-e', 'sh', '-c', f'tty > {filepath}; exec sh'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # 阻塞式檢測，等待 tty 文件生成並寫入內容
    while not os.path.exists(filepath) or os.stat(filepath).st_size == 0:
        time.sleep(0.1)  # 短暫等待，減少 CPU 負擔
    
    return filepath, process.pid

def check_pid(pid):
    """檢查進程是否存在"""
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True

def reset_and_close_all_panels():
    """將所有面板重定向到原始視窗並關閉所有外部視窗"""
    for panel, (tty_var, pid_var) in panel_info.items():
        # 將面板輸出重定向回 gdb 的原始終端
        gdb.execute(f"dashboard {panel} -output {original_tty}")
        
        # 關閉視窗
        panel_pid = globals()[pid_var]
        if panel_pid and check_pid(panel_pid):
            subprocess.run(['kill', str(panel_pid)])
            globals()[tty_var], globals()[pid_var] = None, None
            print(f"Closed {panel} panel with PID {panel_pid}")

def split_window_layout(panels):
    """重定向所有面板並關閉視窗，然後按照 panels 開啟新的布局"""

    # 重置並關閉所有外部視窗
    reset_and_close_all_panels()

    # 過濾無效面板名稱，並移除 source 面板
    valid_panels = [panel for panel in panels if panel in panel_info]

    # 設置 dashboard 布局，包含 source 面板
    layout = "source " + " ".join(valid_panels)
    gdb.execute(f"dashboard -layout {layout}")
    print(f"Dashboard layout set to: {layout}")

    # 記錄要打開的終端文件路徑，稍後一次性讀取
    ttys_to_read = {}

    # 為每個有效面板打開新的終端窗口
    for panel in valid_panels:
        tty_var, pid_var = panel_info[panel]
        
        # 打開新終端並記錄 TTY 和 PID
        ttys_to_read[panel] = open_terminal_and_get_tty(f"/tmp/{panel}_tty")

    # 執行指定次數的切回上一個視窗操作 (Alt+k)，次數等於新開啟的視窗數
    for _ in range(len(valid_panels)):
        subprocess.run(['xdotool', 'key', 'Alt+k'])

    # 配置每個面板的輸出到新打開的終端
    for panel, (tty_filepath, pid) in ttys_to_read.items():
        with open(tty_filepath, 'r') as tty_file:
            tty = tty_file.read().strip()
        os.remove(tty_filepath)

        # 更新全局變量，將面板輸出到新終端
        globals()[panel_info[panel][0]], globals()[panel_info[panel][1]] = tty, pid
        gdb.execute(f"dashboard {panel} -output {tty}")
        print(f"{panel.capitalize()} panel output has been redirected to: {tty}")

    # 顯示 dashboard
    gdb.execute("dashboard")

# 使用 atexit 在退出時自動關閉所有終端
def close_terminals():
    reset_and_close_all_panels()

# 註冊 atexit 函數
atexit.register(close_terminals)

