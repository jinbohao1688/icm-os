#!/bin/bash
# 编译 sample_arm64.c 为真实 ARM64 ELF 二进制
set -e

aarch64-linux-gnu-gcc -O2 -static -o gbt/tests/sample_arm64.elf gbt/tests/sample_arm64.c
echo "编译完成：gbt/tests/sample_arm64.elf"

