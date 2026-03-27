# ICM-OS

**Intent-Centric Meta-Operating System** — A research prototype for AI-driven capability decomposition and generative binary translation.

> 论文全文见作者个人网站： [jinac.pages.dev](https://jinac.pages.dev)

---

## 概述

ICM-OS 是一个意图驱动的元操作系统。用任意语言表达意图，系统自动执行。

**三大核心能力：**

**1. 无限原语扩展**
当注册表中没有合适的原语时，AI 实时生成新原语代码，动态加载执行，并缓存到磁盘供下次直接使用。

**2. 任意格式执行**
用户提交任何文件——Python、Shell、Lua、自创格式、从未见过的 DSL——AI 分析内容，理解语义，转换并执行。无需安装任何运行环境。

**3. 任意语言意图**
中文、英文、德文、日文……任何语言表达意图，AMS 直接理解并提取参数执行。

---

## 当前状态 (v0.1 · M5 完成 · 2026.03)

| 组件 | 状态 | 说明 |
|------|------|------|
| 内核 | ✅ | Linux 6.1.82 LTS，裸机可启动 |
| ICM Shell | ✅ | 意图驱动，24个预定义原语 |
| 动态原语生成 | ✅ | AI 实时生成，自动缓存，重启恢复 |
| SANDBOX_EXEC | ✅ **新** | AI 分析任意格式文件并执行 |
| 自创格式执行 | ✅ **新** | 从未见过的 DSL，AI 转换后运行 |
| 多语言意图 | ✅ | 任意语言，AI 直接提取参数 |
| 文件读写 | ✅ 真实 | 真实 I/O，任意语言写入 |
| 网页抓取+总结 | ✅ 真实 | DNS→TCP→TLS→HTTP→HTML→AI |
| NLP_TRANSLATE | ✅ 真实 | 任意语言互译 |
| 原语缓存 | ✅ | 重启自动恢复，零 API 消耗 |

---

## 核心演示

### 运行任意格式文件

```
# Python 脚本
icm> run /data/examples/fib.py
Result: Fibonacci sequence:
0 1 1 2 3 5 8 13 21 34  ✅

# Shell 脚本
icm> run /data/examples/system_info.sh
Result: === ICM-OS System Info ===
Kernel: Linux 6.1.82  ✅

# 无扩展名文件（AI 分析）
icm> run /data/mystery
[SANDBOX] AI: 这是Python脚本
Result: 1764  ✅

# 自创格式（从未见过的 DSL）
icm> run /data/app.icm
内容: PRINT Hello from ICM format
      PRINT 2+2=4
[SANDBOX] AI: 自定义脚本语言，PRINT可映射为print，转换后用Python执行
Result: Hello from ICM format
        2+2=4  ✅
```

### 动态原语生成 + 缓存

```
# 第一次：AI 生成
icm> use UUID_GENERATE primitive to create a UUID
[DynGen] Generating primitive: UUID_GENERATE
[DynGen] Cached: /data/primitives/UUID_GENERATE.py
Result: bc05d63e-718c-4ea6-804c-a1eeef3b83d1  ✅

# 重启后：从缓存加载，零 API
[DynGen] Loaded from cache: UUID_GENERATE
Result: 5d604c9e-eafb-4ae1-beb4-6a7e36bd31d8  ✅（无 API 调用）
```

### 任意语言意图

```
# 中文
icm> 把"你好世界"写入文件 /data/notes/chinese.txt
→ 你好世界  ✅

# 德文
icm> Schreibe "Hallo Welt" in die Datei /data/notes/german.txt
→ Hallo Welt  ✅

# 中文抓取总结
icm> 抓取 https://example.com 并总结内容
→ 此域名仅用于文档示例，无需授权，请勿用于实际操作。  ✅
```

### 系统信息读取

```
icm> show current memory usage
→ MemTotal: 1023272 kB  MemFree: 841840 kB  ✅（真实内核数据）

icm> use PROCESS_LIST primitive to show all running processes
→ [{"PID": "1", "COMMAND": "/usr/bin/python3 /icm-os/icm_shell.py"}...]  ✅
```

---

## 系统架构

```
用户输入自然语言意图（任意语言）
        ↓
   AMS 意图分解器 (DeepSeek API)
   ├─ 提取参数 (url/path/content/target_lang...)
   └─ 发现缺失原语 → 触发 DynGen
        ↓
  ┌──────────────────────────────────────────────┐
  │  DynGen 动态原语生成                            │
  │  缺失原语 → AI 生成代码 → exec() 加载           │
  │  → 注册到 CPR → 保存到 /data/primitives        │
  │  → 重启后自动恢复                               │
  └──────────────────────────────────────────────┘
        ↓
  CDM Capability Graph
        ↓
  ┌──────────────────────────────────────────────┐
  │  原语执行器                                     │
  │                                              │
  │  SANDBOX_EXEC ← AI分析任意格式，转换执行        │
  │  DNS/HTTP/TLS  ← 真实网络                      │
  │  FILE_*        ← 真实文件 I/O                  │
  │  NLP_*         ← 真实 AI                      │
  │  动态生成原语   ← 无限扩展                       │
  └──────────────────────────────────────────────┘
        ↓
     执行结果
```

**底层系统栈：**

```
ICM Shell (Python 3.10)
  24 预定义原语 + 无限动态原语
  SANDBOX_EXEC（AI驱动任意格式执行）
        ↓
Linux 6.1.82（最小化内核）
  e1000 + TCP/IP + tmpfs
        ↓
QEMU x86-64 / 裸机
```

---

## 快速开始

### 配置

```bash
git clone https://github.com/jinbohao1688/icm-os.git
cd icm-os
echo "DEEPSEEK_API_KEY=your_key_here" > .env
```

### 开发模式

```bash
pip install -r requirements.txt
python3 cli.py
```

### 构建 ISO

```bash
sudo apt install -y build-essential gcc make xorriso \
    grub-pc-bin grub-common busybox-static \
    libelf-dev libssl-dev bc flex bison qemu-system-x86

chmod +x iso-build/build.sh && ./iso-build/build.sh
```

### 启动

```bash
qemu-system-x86_64 \
  -kernel iso-build/work/iso/boot/vmlinuz \
  -initrd iso-build/work/initrd.img \
  -append "console=ttyS0,115200n8 rdinit=/init" \
  -m 1024M -nographic \
  -netdev user,id=net0 -device e1000,netdev=net0
```

### 重建 initramfs

```bash
bash iso-build/rebuild_initrd.sh
```

---

## 预定义原语（24个）

| 类别 | 原语 | 状态 |
|---|---|---|
| 执行 | `SANDBOX_EXEC` | ✅ AI驱动，任意格式 |
| 网络 | `DNS_RESOLVE` `TCP_CONNECT` `TLS_HANDSHAKE` `HTTP_GET` `HTTP_POST` | ✅ 真实 |
| NLP | `NLP_TRANSLATE` `NLP_SUMMARIZE` `NLP_ENCODE` | ✅ 真实 |
| 文件 | `FILE_OPEN` `FILE_READ` `FILE_WRITE` `FILE_CLOSE` | ✅ 真实 |
| 渲染 | `HTML_PARSE` | ✅ 真实 |
| 其他 | `CSS_LAYOUT` `JS_EXECUTE` `WINDOW_RENDER` `UTF8_DECODE` 等 | mock |
| 有状态 | `SESSION_STORE` `CACHE_LAYER` `FILE_STATE` | 实现 |

**动态生成原语示例：**

| 原语 | 功能 |
|---|---|
| `UUID_GENERATE` | 生成随机 UUID |
| `SHA256_HASH` | 计算 SHA256 |
| `BASE64_ENCODE` | Base64 编码 |
| `PROCESS_LIST` | 列出进程 |
| `RANDOM_PASSWORD` | 生成随机密码 |
| `CODE_GENERATE` | AI 生成代码 |
| `...` | 用户需要什么，AI 就生成什么 |

---

## 里程碑

| 阶段 | 状态 | 内容 |
|---|---|---|
| M1 | ✅ | 可启动 ISO + CDM + 网络（2026.03） |
| M2 | ✅ | 真实 DNS / HTTP / 翻译（2026.03） |
| M3 | ✅ | FILE_READ/WRITE + HTML_PARSE + NLP_SUMMARIZE（2026.03） |
| M4 | ✅ | 动态原语生成，系统自我扩展（2026.03） |
| M5 | ✅ | SANDBOX_EXEC，零配置运行任意格式（2026.03） |
| M6 | 📋 | 原语安全沙箱 + 依赖自动安装 |
| M7 | 📋 | C/Rust 核心 + 性能优化 |
| M8 | 📋 | 稳定发行版 v1.0 |

---

## 未来愿景

```
icm> 运行这个 Flutter 项目 /data/myapp
→ DEPENDENCY_SCAN: 检测到 Dart/Flutter 项目
→ ENV_BUILD: 自动下载 Flutter SDK
→ SANDBOX_EXEC: 编译并运行
→ 返回输出

无需用户安装任何东西。
Python、Node.js、Rust、Flutter、任何语言，同理。
甚至是你自己发明的编程语言。
```

---

## 技术选型

| 层 | 当前 | 未来 |
|----|------|------|
| 内核 | Linux 6.1.82 | 自研微内核 |
| 运行时 | Python 3.10 | Rust + PyO3 |
| 原语扩展 | AI 动态生成 + 磁盘缓存 | 编译缓存 + Wasm 沙箱 |
| 文件执行 | AI 分析转换 | 更快的本地推理 |
| 意图分解 | DeepSeek API | 本地小模型 |

---

## 参考论文

- [jinac.vxni.ink](https://jinac.vxni.ink)
- [jinac.pages.dev](https://jinac.pages.dev)

---

## License

MIT License

---

*ICM-OS is a research prototype. Not for production use.*
