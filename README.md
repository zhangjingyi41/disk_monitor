# 硬盘状态监听器 (Disk Monitor)

实时监控磁盘读写活动，支持 Windows 和 Linux 平台。

## 功能特性

- **磁盘活动监控**：实时检测磁盘读写操作
- **进程归因**：显示发生读写操作的进程 PID 和名称
- **速率计算**：实时计算读写速率 (KB/s)
- **自适应刷新**：
  - 活跃期：默认 300ms 刷新
  - 空闲期：默认 1500ms 刷新
- **跨平台支持**：Windows (ETW)、Linux (psutil)
- **GUI 扩展接口**：支持自定义界面实现
- **降级模式**：高级功能不可用时自动切换到 psutil 近似模式

## 界面预览

```
==================================================
刷新间隔: 300ms | 时间: 2024-01-15 10:30:45
==================================================

Disk: C:
  Status: READ
  Pid: 8778
  ProcessName: QQ.exe
  Rate: 137.4KB/s

Disk: D:
  Status: WRITE
  Pid: 8779
  ProcessName: vscode.exe
  Rate: 4.3KB/s
```

## 依赖

- Python 3.10+
- psutil >= 5.9.0

## 安装

### 1. 克隆项目

```bash
git clone <repository-url>
cd disk_monitor
```

### 2. 创建虚拟环境

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# 或
.venv\Scripts\activate      # Windows
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

## 运行

### 基本用法

```bash
python main.py
```

### 命令行参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--window-ms` | 1000 | 聚合窗口大小 (毫秒) |
| `--active-refresh-ms` | 300 | 活跃期刷新间隔 (毫秒) |
| `--idle-refresh-ms` | 1500 | 空闲期刷新间隔 (毫秒) |
| `--top-n` | 10 | 每磁盘展示的最多进程数 |
| `--approx-mode` | False | 强制使用近似模式 |

### 示例

```bash
# 1秒刷新一次
python main.py --active-refresh-ms 1000

# 200ms高频刷新
python main.py --active-refresh-ms 200 --idle-refresh-ms 500

# 仅显示 Top 5 活跃进程
python main.py --top-n 5
```

## 测试

### 运行所有测试

```bash
pytest tests/ -v
```

### 查看测试覆盖率

```bash
pytest tests/ --cov=. --cov-report=term-missing
```

## 项目结构

```
disk_monitor/
├── core/
│   ├── aggregator.py         # 时间窗聚合、速率计算
│   ├── collector.py          # 采集器工厂
│   ├── collector_base.py    # 采集器抽象接口
│   ├── collector_windows.py # Windows ETW 采集
│   ├── collector_linux.py   # Linux psutil 采集
│   ├── disk_scanner.py      # 磁盘扫描
│   ├── models.py            # 数据模型
│   └── process_cache.py     # 进程名缓存 (TTL)
├── ui/
│   ├── callback.py          # GUI 回调接口
│   └── display.py           # CLI 显示实现
├── utils/
│   ├── config.py           # 命令行参数解析
│   └── platform.py          # 平台检测
├── tests/                   # 单元测试
├── main.py                  # 程序入口
└── requirements.txt
```

## GUI 扩展

程序使用回调模式，可轻松接入自定义 GUI：

```python
from ui.callback import OutputCallback
from core.models import DiskActivity
from typing import List

class MyGUIOutput(OutputCallback):
    def output(self, activities: List[DiskActivity], interval_ms: int) -> None:
        # 自定义显示逻辑
        for activity in activities:
            print(f"{activity.disk}: {activity.process_name}")

    def set_refresh_interval(self, interval_ms: int) -> None:
        self._interval = interval_ms

# 使用自定义 GUI
monitor = DiskMonitor(config, MyGUIOutput())
monitor.start()
```

## 打包

### Windows 打包 (使用 PyInstaller)

```bash
pip install pyinstaller
pyinstaller --onefile --name disk_monitor main.py
```

生成的 exe 文件位于 `dist/` 目录。

### Linux 打包

```bash
pip install pyinstaller
pyinstaller --onefile --name disk_monitor main.py
chmod +x dist/disk_monitor
```

## 注意事项

- Windows 下首次运行可能需要管理员权限以访问 ETW 事件
- WSL 环境下监控的是 WSL 内部的磁盘访问
- 近似模式下进程与磁盘归因可能不精确

## License

MIT License
