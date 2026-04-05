# ICM-OS

**Intent-Centric Meta-Operating System** — 意图驱动的元操作系统，AI 原生设计，支持自研内核。

> 论文全文：[jinac.vxni.ink](https://jinac.vxni.ink) · [jinac.pages.dev](https://jinac.pages.dev)

---

## 概述

ICM-OS 是一个意图驱动的元操作系统。用任意语言表达意图，系统自动分解并执行。

**四大核心能力：**

**1. 无限原语扩展**
注册表中没有合适的原语时，AI 实时生成代码，动态加载执行，缓存到磁盘，重启自动恢复。

**2. 任意格式执行**
任何文件——Python、Shell、Lua、自创格式、从未见过的 DSL——AI 分析内容，理解语义，转换并执行。无需安装任何运行环境。

**3. 任意语言意图**
中文、英文、德文、日文……任何语言表达意图，AMS 直接理解并提取参数执行。

**4. 自研内核（新）**
ICM-OS C Shell 现已成功运行在 Synapse Kernel（自研 i386 内核）上，完全脱离 Linux。

---

## 当前状态 (v0.3 · 2026.04)

| 组件 | 状态 | 说明 |
|------|------|------|
| Python Shell | ✅ | 意图驱动，CDM: yes，24个原语，AI 动态生成 |
| C Shell | ✅ | 纯 C99，零依赖，裸机启动 |
| C 原语库 | ✅ | file/dns/http/shell_exec，纯系统调用 |
| C AMS | 🔄 | curl 调用 DeepSeek，C 版意图分解 |
| 动态原语生成 | ✅ | AI 实时生成，缓存，重启恢复 |
| SANDBOX_EXEC | ✅ | AI 分析任意格式文件并执行 |
| 多语言意图 | ✅ | 任意语言，AI 直接提取参数 |
| **Synapse Kernel** | ✅ **新** | 自研 i386 内核，icm_shell 成功运行 |
| **分页内存管理** | ✅ **新** | 自研 frame allocator + 4级页表，无 triple fault |
| **ELF 加载器** | ✅ **新** | 用户态 ELF 加载执行 |
| **VFS/TmpFS** | ✅ **新** | 虚拟文件系统 + 内存文件系统 |
| Env Engine | 📋 | AI 驱动的安全环境变量管理 |
| ISO 发布版 | 📋 | GRUB 引导，可直接刻盘启动 |

---

## 两种运行模式

### Python 模式（功能完整）

```bash
qemu-system-x86_64 \
  -kernel iso-build/work/iso/boot/vmlinuz \
  -initrd iso-build/work/initrd.img \
  -append "console=ttyS0,115200n8 rdinit=/init" \
  -m 1024M -nographic \
  -netdev user,id=net0 -device e1000,netdev=net0
```

```
ICM-OS shell (intent-driven). Primitives: 24. CDM: yes
icm> 抓取 https://example.com 并总结内容
icm> use UUID_GENERATE primitive to create a UUID
icm> run /data/app.icm
```

### C 模式（零依赖，极速）

```bash
cd c-primitives && make icm_shell && ./icm_shell
```

```
Intent-Centric Meta Operating System v0.1 (C edition)
icm> !echo hello from bare metal C
icm> fetch http://example.com
icm> dns github.com
```

### Synapse Kernel 模式（自研内核）⭐ 新

```bash
cd Synapse-Kernel
make && qemu-system-i386 -kernel synapse.bin -m 128M -nographic -no-reboot
```

```
Synapse OS v0.1
AI-Native Operating System
Initializing...
[OK] Paging initialized
[OK] Kernel heap initialized
[OK] Filesystem initialized
synapse> /bin/icm_shell

  ICM-OS Shell [Synapse Kernel]
  Type 'help' for commands, 'exit' to quit.

icm> help
  help    - show this help
  read    - read file contents
  write   - write file
  exit    - exit shell
```

---

## Synapse Kernel 架构

自研 i386 裸机内核，从零实现：

```
Synapse Kernel
├── 引导层        boot.asm（Multiboot2，直接进保护模式）
├── 内存管理
│   ├── Frame Allocator（bitmap，0-8MB 保留）
│   ├── 分页（PD/PT 固定物理地址，identity-map 0-8MB）
│   └── Kernel Heap（0xC0000000，bump allocator）
├── 中断处理      IDT，256个门，timer/keyboard IRQ
├── 进程管理      PCB，调度器，ELF 加载器
├── 文件系统      VFS + TmpFS + ProcFS
├── 系统调用      int 0x80，11个调用
│   └── exit/fork/wait/write/read/open/close/mmap/munmap/sbrk/execve
└── 用户态        /bin/icm_shell（ELF，embed 进内核）
```

---

## 核心演示

### 在自研内核上运行 icm_shell

```
synapse> /bin/icm_shell
[ELF] loaded /bin/icm_shell, entry=0x00400000
[EXEC] jumping to entry

  ICM-OS Shell [Synapse Kernel]

icm> help
ICM-OS Shell commands:
  help    - show this help
  version - show version
  exit    - exit shell
  read    - read and print file contents
  write   - create/truncate file with text
  !<cmd>  - fork+exec program
```

### 动态原语生成 + 缓存（Python 模式）

```
# 第一次：AI 生成
icm> use UUID_GENERATE primitive to create a UUID
[DynGen] Generating primitive: UUID_GENERATE
[DynGen] Cached: /data/primitives/UUID_GENERATE.py
Result: bc05d63e-718c-4ea6-804c-a1eeef3b83d1  ✅

# 重启后：从缓存加载，零 API 调用
[DynGen] Loaded from cache: UUID_GENERATE
Result: 5d604c9e-...  ✅
```

### 任意语言写文件

```
icm> 把"你好世界"写入文件 /data/notes/chinese.txt  ✅
icm> Schreibe "Hallo Welt" in die Datei /data/notes/german.txt  ✅
```

### 真实 DNS + HTTP（C 版）

```
icm> fetch http://example.com
[HTTP_GET] ok code=200 body_bytes=540  ✅

icm> dns github.com
[DNS_RESOLVE] ok ip=20.205.243.166 ttl=300  ✅
```

---

## C 原语库

纯 C99 实现，零第三方依赖：

| 原语 | 实现 | 说明 |
|------|------|------|
| `file_primitive` | `fopen/fread/fwrite/opendir` | 文件读写列目录 |
| `shell_exec` | `fork/execvp/pipe/waitpid` | 命令执行，支持 timeout |
| `dns_resolve` | `getaddrinfo/inet_ntop` | 真实 DNS，IPv4+IPv6 |
| `http_get` | `socket/connect/send/recv` | 纯 socket HTTP/1.1 |
| `ams` | `curl + DeepSeek API` | C 版意图分解 |

```bash
cd c-primitives
make test        # 运行所有测试
make icm_shell   # 编译 C 版 shell
make run         # 运行 C 版 shell
```

---

## 系统架构

```
用户输入自然语言意图（任意语言）
        ↓
   AMS 意图分解器
   ├─ Python 版：DeepSeek API + networkx DAG
   └─ C 版：curl + DeepSeek API
        ↓
  CDM Capability Graph
        ↓
  ┌─────────────────────────────────────────────┐
  │  原语执行器                                   │
  │                                             │
  │  Python 层（24个预定义 + 无限动态生成）          │
  │  ├─ SANDBOX_EXEC ← AI分析任意格式文件          │
  │  ├─ DNS/HTTP/TLS  ← 真实网络                  │
  │  ├─ FILE_*        ← 真实文件 I/O              │
  │  └─ NLP_*         ← 真实 AI                  │
  │                                             │
  │  C 层（零依赖，直接系统调用）                    │
  │  ├─ file_primitive ← fopen/fread/fwrite      │
  │  ├─ shell_exec     ← fork/execvp             │
  │  ├─ dns_resolve    ← getaddrinfo             │
  │  └─ http_get       ← pure socket             │
  └─────────────────────────────────────────────┘
        ↓
Synapse Kernel（自研 i386）/ Linux 6.1.82（备用）
```

---

## 里程碑

| 阶段 | 状态 | 内容 |
|------|------|------|
| M1 | ✅ | 可启动 ISO + CDM + 网络 |
| M2 | ✅ | 真实 DNS / HTTP / 翻译 |
| M3 | ✅ | FILE_READ/WRITE + HTML_PARSE + NLP_SUMMARIZE |
| M4 | ✅ | 动态原语生成，系统自我扩展 |
| M5 | ✅ | SANDBOX_EXEC，任意格式文件执行 |
| M6 | ✅ | C 原语库 + C 版 shell，零依赖 |
| M7 | ✅ | Synapse Kernel 融合，icm_shell 跑在自研内核 |
| M8 | 📋 | Env Engine，AI 驱动的安全环境管理 |
| M9 | 📋 | 稳定发行版 v1.0，GRUB 引导 ISO |

---

## 快速开始

```bash
# Python 模式（功能最完整）
git clone https://github.com/jinbohao1688/icm-os.git
cd icm-os
echo "DEEPSEEK_API_KEY=your_key" > .env
pip install -r requirements.txt
python3 cli.py

# C 模式（零依赖）
cd c-primitives && make icm_shell && ./icm_shell

# Synapse Kernel 模式（自研内核）
git clone https://github.com/jinbohao1688/Synapse-Kernel.git
cd Synapse-Kernel && make
qemu-system-i386 -kernel synapse.bin -m 128M -nographic -no-reboot
```

---

## 项目结构

```
icm-os/
├── ams/              # 意图分解器（Python）
│   ├── decomposer.py # DeepSeek API + DAG
│   └── dynamic_gen.py# 动态原语生成
├── primitives/       # 24个预定义原语
│   ├── stateless/    # network/nlp/file/rendering
│   └── stateful/     # cache/session/file_state
├── c-primitives/     # C 原语库
│   ├── file_primitive.c
│   ├── shell_exec.c
│   ├── dns_resolve.c
│   ├── http_get.c
│   ├── ams.c
│   └── icm_shell.c   # C 版 shell
└── iso-build/        # ISO 构建系统

Synapse-Kernel/
├── kernel/
│   ├── boot/         # Multiboot2 引导
│   ├── mm/           # 内存管理（paging + heap）
│   ├── proc/         # 进程调度 + ELF 加载
│   ├── fs/           # VFS + TmpFS + ProcFS
│   └── syscall.c     # 11个系统调用
├── lib/              # 驱动库（vga/serial/keyboard）
└── apps/icm_shell/   # 用户态 icm_shell
```

---

## 参考论文

- [jinac.vxni.ink](https://jinac.vxni.ink)
- [jinac.pages.dev](https://jinac.pages.dev)

---

## License

MIT License

---

*ICM-OS 是研究原型，不用于生产环境。*
*核心价值：验证"意图驱动"的人机交互模型。*
