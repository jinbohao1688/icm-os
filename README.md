# ICM-OS

[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10-blue)](https://www.python.org/)
[![Linux Kernel](https://img.shields.io/badge/Linux-6.1-orange)](https://www.kernel.org/)

**Intent-Centric Meta-Operating System** — 面向 AI 驱动能力分解与生成式二进制翻译的研究原型。

> 论文全文见作者个人网站：[jinac](https://jinac.pages.dev)

---

## 📖 目录

- [概述](#概述)
- [当前状态](#当前状态v01-·-202603)
- [仓库结构](#仓库结构节选)
- [架构概览](#架构概览)
- [快速开始](#快速开始)
- [演示片段](#演示片段概念)
- [预定义原语](#预定义原语python-侧-·-节选)
- [Env Engine](#env-engineai-驱动的环境管理)
- [里程碑](#里程碑)
- [未来愿景](#未来愿景节选)
- [技术选型](#技术选型)
- [参考论文](#参考论文)
- [License](#license)

---

## 概述

ICM-OS 是一个 **意图驱动** 的元操作系统：用自然语言描述意图，系统将其分解为 **能力原语** 并执行。

**核心方向：**

1. **无限原语扩展**：缺少原语时 AI 生成并动态加载。
2. **任意格式执行**：支持 Python、Shell、Lua、自定义 DSL 等。
3. **任意语言意图**：AMS 映射多语言意图为原语执行。
4. **AI 驱动环境管理**：安全应用环境配置（Env Patch），支持会话隔离和回滚。

---

## 当前状态 (v0.1 · 2026.03)

| 组件 | 状态 | 说明 |
|------|------|------|
| Linux 内核 | ✅ | 6.1.x LTS，`iso-build/build.sh` 可构建可启动 ISO |
| ICM Shell (Python) | ✅ | `cli.py` / `iso-build/icm_shell.py`，DeepSeek AMS + 能力图执行 |
| ICM Shell (C) | ✅ **新** | `c-primitives/icm_shell`，关键词路由 + AMS，无 Python 亦可交互 |
| C 原语库 | ✅ **新** | `c-primitives/`：FILE_*, SHELL_EXEC, DNS_RESOLVE, HTTP_GET, ams.c |
| initramfs / ISO | ✅ | 打包静态 icm_shell、Python 运行时与网络配置 |
| GBT | 🔧 | 生成式二进制翻译实验路径 ARM64→x86-64 |
| 动态原语生成 (Python) | ✅ | AI 生成原语，缓存至 ~/.icm-os/primitives |
| SANDBOX_EXEC | ✅ | 任意格式文件分析执行 |
| Env Engine | 📋 设计中 | 会话隔离 + 持久化确认 |

---

## 仓库结构（节选）

| 路径 | 含义 |
|------|------|
| `ams/`、`core/`、`primitives/`、`security/` | Python 运行时：CPR、能力图、策略、预定义原语 |
| `cli.py` | 本地开发用交互 CLI（Rich 界面） |
| `c-primitives/` | C99 原语与 icm_shell |
| `iso-build/` | 内核 / busybox / initramfs / GRUB ISO |
| `gbt/` | 语义提升与合成管线（实验） |
| `env-engine/` | 环境管理子系统（规划中） |

---

## 架构概览

<details>
<summary>点击展开架构图</summary>

```text
自然语言意图（任意语言）
↓
┌───────────────────────────────┐
│ AMS（意图分解，DeepSeek API） │
└───────────────────────────────┘
↓
能力图（Python） / 单原语路由（C shell）
↓
┌───────────────────────────────┐
│ 原语执行                     │
└───────────────────────────────┘
↓
┌───────────────────────────────┐
│ Env Engine（环境管理）        │
└───────────────────────────────┘
↓
执行结果

</details>
---

快速开始

<details>
<summary>点击展开安装与运行</summary>配置

git clone https://github.com/jinbohao1688/icm-os.git
cd icm-os
echo "DEEPSEEK_API_KEY=your_key_here" > .env

Python 开发模式

pip install -r requirements.txt
python3 cli.py

C 原语与 C shell

cd c-primitives
make icm_shell
export DEEPSEEK_API_KEY=your_key_here
make run

构建 ISO

sudo apt install -y build-essential gcc make xorriso \
  grub-pc-bin grub-common wget libelf-dev libssl-dev bc flex bison qemu-system-x86
chmod +x iso-build/build.sh && ./iso-build/build.sh

QEMU 启动示例

qemu-system-x86_64 \
  -kernel iso-build/work/iso/boot/vmlinuz \
  -initrd iso-build/work/initrd.img \
  -append "console=ttyS0,115200n8 rdinit=/init" \
  -m 1024M -nographic \
  -netdev user,id=net0 -device e1000,netdev=net0

</details>
---

演示片段（概念）

Python CLI：自然语言 → AMS 分解 → 能力图执行

C Shell：关键词驱动，AMS 返回 JSON → 调用对应 C 原语



---

预定义原语（Python 侧 · 节选）

类别	示例原语

执行	SANDBOX_EXEC
网络	DNS_RESOLVE、HTTP_GET、HTTP_POST
NLP	NLP_TRANSLATE、NLP_SUMMARIZE
文件	FILE_READ、FILE_WRITE


C 原语

符号	作用

icm_file_read/write/list	文件操作
icm_shell_exec	fork+execvp
icm_dns_resolve	getaddrinfo + inet_ntop
icm_http_get	HTTP GET
icm_ams_decompose	curl 调 DeepSeek，解析 JSON



---

Env Engine

<details>
<summary>点击展开 Env Engine 说明</summary>核心理念：AI 输出结构化 Env Patch，由系统安全应用

示例 Patch：


{
  "type": "env_patch",
  "operations": [
    {"op": "set", "key": "FLUTTER_HOME", "value": "/opt/flutter"},
    {"op": "append_path", "value": "$FLUTTER_HOME/bin"}
  ]
}

执行流程：

1. 接收 Patch 更新会话环境


2. 注入子进程


3. 用户确认后持久化至 .bashrc 并备份



安全约束：

❌ 禁止直接写入 /etc

❌ 禁止覆盖关键变量

✅ 会话隔离，白名单验证



</details>
---

里程碑

阶段	状态	内容

M1–M5	✅	可启动 ISO、真实网络/文件、动态原语、SANDBOX_EXEC
—	✅	C 原语 + C icm_shell + AMS 集成
M6	📋	原语安全沙箱 + Env Engine 基础实现
M7	📋	核心性能优化 + Env Engine 持久化/回滚
M8	📋	稳定发行版 v1.0 + 完整环境管理能力



---

未来愿景

在任意语言/格式上「说意图即执行」，结合小模型降低 API 依赖；运行时与沙箱向 Rust/Wasm 演进；Env Engine 实现“AI 定义环境，系统安全构建”。


---

技术选型

层	当前	方向

内核	Linux 6.1 LTS	可自研或裁剪
意图分解	DeepSeek API	本地小模型
运行时	Python 3.10 + 原语注册表	Rust + PyO3/扩展
C 原语	C99 + POSIX	无 Python 启动路径
环境管理	Python/C（规划中）	会话隔离 + 持久化 + 容器后端



---

参考论文

jinac.vxni.ink

jinac.pages.dev



---

License

MIT License

> ICM-OS 为研究原型，不用于生产环境关键业务。



---