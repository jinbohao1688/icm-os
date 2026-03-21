# ICM-OS ISO build

Build a bootable ICM-OS ISO (Linux 6.1 LTS + busybox initramfs + GRUB2).

## Requirements (Ubuntu 22.04 / WSL2)

```bash
sudo apt-get install -y build-essential libncurses-dev bc flex bison \
  libssl-dev libelf-dev xorriso grub-pc-bin grub-common wget
```

Optional (for intent-driven shell on the ISO): `python3`, `python3-pip`.

## Build

From repo root:

```bash
./iso-build/build.sh
```

Output: `iso-build/icm-os.iso`.

## Test with QEMU

```bash
qemu-system-x86_64 -cdrom iso-build/icm-os.iso -m 512M
```

For serial console: add `-serial stdio` and use `console=ttyS0` (already in grub.cfg).

## Layout

- **build.sh** – Downloads kernel 6.1 LTS, builds tinyconfig+kernel, busybox, initramfs, copies ICM-OS runtime, runs grub-mkrescue.
- **initramfs/init** – PID 1: mounts `/proc`, `/sys`, `/dev`, then starts `icm_shell.py` (if Python available) or `/bin/sh`.
- **icm_shell.py** – Intent-driven shell: CDM decompose → capability graph execution; fallback to traditional commands. Prefix a line with `!` to run as command only.
- **grub/grub.cfg** – Single entry “ICM-OS”, 5s timeout, `console=ttyS0,115200n8 console=tty0`.
