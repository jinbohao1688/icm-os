# ICM-OS

**Intent-Centric Meta-Operating System** — A research prototype for AI-driven capability decomposition and generative binary translation.

> 论文全文见作者个人网站：[jinac.vxni.ink](https://jinac.vxni.ink) · [jinac.pages.dev](https://jinac.pages.dev)

---

## 概述

ICM-OS 是一个意图驱动的元操作系统。用任意语言表达意图，系统自动执行。

**四大核心能力：**

**1. 无限原语扩展**
注册表中没有合适的原语时，AI 实时生成代码，动态加载执行，缓存到磁盘，重启自动恢复。

**2. 任意格式执行**
任何文件——Python、Shell、Lua、自创格式、从未见过的 DSL——AI 分析内容，理解语义，转换并执行。无需安装任何运行环境。

**3. 任意语言意图**
中文、英文、德文、日文……任何语言表达意图，AMS 直接理解并提取参数执行。

**4. C 原语层（新）**
核心原语用纯 C99 重写，零依赖，直接系统调用，C 版 shell 可在裸机上独立运行。

---

## 当前状态 (v0.2 · 2026.03)

| 组件 | 状态 | 说明 |
|------|------|------|
| 内核 | ✅ | Linux 6.1.82 LTS，裸机可启动 |
| Python Shell | ✅ | 意图驱动，CDM: yes，24个原语，AI 动态生成 |
| **C Shell** | ✅ **新** | 纯 C99，零 Python，零依赖，裸机启动 |
| **C 原语库** | ✅ **新** | file/dns/http/shell_exec，纯系统调用 |
| **C AMS** | 🔄 进行中 | curl 调用 DeepSeek，C 版意图分解 |
| 动态原语生成 | ✅ | AI 实时生成，缓存，重启恢复 |
| SANDBOX_EXEC | ✅ | AI 分析任意格式文件并执行 |
| 多语言意图 | ✅ | 任意语言，AI 直接提取参数 |
| 文件读写 | ✅ 真实 | 真实 I/O |
| 网页抓取+总结 | ✅ 真实 | DNS→TCP→TLS→HTTP→HTML→AI |
| NLP_TRANSLATE | ✅ 真实 | 任意语言互译 |
| Synapse 融合 | 🔄 进行中 | 移植到自研 i386 内核 |
| Env Engine | 📋 计划中 | AI 驱动的安全环境变量管理 |

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

---

## 核心演示

### 运行自创格式文件

```
icm> run /data/app.icm
内容: PRINT Hello from ICM format
      PRINT 2+2=4
[SANDBOX] AI: 自定义DSL，PRINT映射为print，转换后用Python执行
Result: Hello from ICM format / 2+2=4  ✅
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
Result: 5d604c9e-...  ✅
```

### 任意语言写文件

```
icm> 把"你好世界"写入文件 /data/notes/chinese.txt → 你好世界 ✅
icm> Schreibe "Hallo Welt" in die Datei /data/notes/german.txt → Hallo Welt ✅
```

### 真实 DNS + HTTP（C 版）

```
icm> fetch http://example.com
[HTTP_GET] ok url=http://example.com code=200 body_bytes=540
[ICM] HTTP 200  ✅

icm> dns github.com
[DNS_RESOLVE] ok domain=github.com ip=20.205.243.166 ttl=300  ✅
```

### 系统信息读取

```
icm> show current memory usage
MemTotal: 1023272 kB  MemFree: 841840 kB  ✅（真实内核数据）
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
   └─ C 版：curl + DeepSeek API + 简单路由
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
Linux 6.1.82 / Synapse Kernel（自研 i386 内核，进行中）
```

---

## Env Engine（计划中）

AI 驱动的安全环境变量管理系统：

```
icm> 帮我配置 Flutter 开发环境
→ ENV_PATCH: {"op": "set", "key": "FLUTTER_HOME", "value": "/opt/flutter"}
→ ENV_PATCH: {"op": "append_path", "value": "$FLUTTER_HOME/bin"}
→ SANDBOX_EXEC: flutter doctor
→ 结果：环境就绪，不污染全局系统
```

**核心设计：**
- AI 输出 `env_patch`（JSON 操作），不直接写 shell 配置
- Session 级隔离，每个会话独立环境
- 可回滚，用户确认后才持久化
- 禁止覆盖系统关键变量

---

## 与 Synapse Kernel 融合

ICM-OS 正在移植到 Synapse Kernel（自研 i386 内核）：

```
Synapse Kernel（自研引导/内存/进程/VFS）
        ↓
ICM-OS C Shell 作为第一个用户态进程（PID 1）
        ↓
C 原语层（file/dns/http/exec）
        ↓
AMS 意图分解
```

目标：完全脱离 Linux，跑在自研内核上。

---

## 快速开始

```bash
git clone https://github.com/jinbohao1688/icm-os.git
cd icm-os
echo "DEEPSEEK_API_KEY=your_key" > .env
pip install -r requirements.txt
python3 cli.py   # 开发模式，不需要内核
```

---

## 项目结构

```
icm-os/
├── ams/              # 意图分解器（Python）
│   ├── decomposer.py # DeepSeek API + DAG
│   └── dynamic_gen.py# 动态原语生成
├── core/             # 执行引擎
├── primitives/       # 24个预定义原语
│   ├── stateless/    # network/nlp/file/rendering
│   └── stateful/     # cache/session/file_state
├── gbt/              # ARM64→x86-64 翻译
├── c-primitives/     # C 原语库（新）
│   ├── file_primitive.c
│   ├── shell_exec.c
│   ├── dns_resolve.c
│   ├── http_get.c
│   ├── ams.c
│   └── icm_shell.c   # C 版 shell
├── iso-build/        # ISO 构建系统
│   ├── build.sh
│   ├── rebuild_initrd.sh
│   └── icm_shell.py  # Python 版 shell
└── cli.py            # 开发模式 CLI
```

---

## 里程碑

| 阶段 | 状态 | 内容 |
|---|---|---|
| M1 | ✅ | 可启动 ISO + CDM + 网络 |
| M2 | ✅ | 真实 DNS / HTTP / 翻译 |
| M3 | ✅ | FILE_READ/WRITE + HTML_PARSE + NLP_SUMMARIZE |
| M4 | ✅ | 动态原语生成，系统自我扩展 |
| M5 | ✅ | SANDBOX_EXEC，任意格式文件执行 |
| M6 | ✅ | C 原语库 + C 版 shell，零依赖 |
| M7 | 🔄 | Synapse Kernel 融合，自研内核 |
| M8 | 📋 | Env Engine，安全环境管理 |
| M9 | 📋 | 稳定发行版 v1.0 |

---

## 参考论文

- [jinac.vxni.ink](https://jinac.vxni.ink)
- [jinac.pages.dev](https://jinac.pages.dev)

---

## License

MIT License

---

*ICM-OS is a research prototype. Not for production use.*
