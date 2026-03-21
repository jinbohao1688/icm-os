#!/usr/bin/env bash
# ICM-OS ISO build script for Ubuntu 22.04 (WSL2).
# Builds: Linux 6.1 LTS kernel, busybox initramfs, GRUB2 bootable ISO.
set -e

ICM_OS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${ICM_OS_ROOT}/iso-build/work"
KERNEL_VERSION="6.1.82"
KERNEL_URL="https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-${KERNEL_VERSION}.tar.xz"
BUSYBOX_VERSION="1.36.1"
BUSYBOX_URL="https://busybox.net/downloads/busybox-${BUSYBOX_VERSION}.tar.bz2"
ISO_DIR="${BUILD_DIR}/iso"
INITRAMFS_DIR="${BUILD_DIR}/initramfs"
OUTPUT_ISO="${ICM_OS_ROOT}/iso-build/icm-os.iso"

echo "[ICM-OS] Build directory: ${BUILD_DIR}"
mkdir -p "${BUILD_DIR}"
cd "${BUILD_DIR}"

# --- 1) Install build dependencies (optional; fail gracefully if not root) ---
install_deps() {
    if command -v apt-get &>/dev/null; then
        echo "[ICM-OS] Checking build dependencies..."
        for pkg in build-essential libncurses-dev bc flex bison libssl-dev libelf-dev xorriso grub-pc-bin grub-common; do
            if ! dpkg -l "$pkg" &>/dev/null; then
                echo "[ICM-OS] Install with: sudo apt-get install -y $pkg (and optionally: python3 python3-pip)"
                return 1
            fi
        done
    fi
    return 0
}
install_deps || true

# --- 2) Download and build Linux 6.1 LTS kernel ---
kernel_src="${BUILD_DIR}/linux-${KERNEL_VERSION}"
if [[ ! -d "${kernel_src}" ]]; then
    echo "[ICM-OS] Downloading kernel ${KERNEL_VERSION}..."
    wget -q -O "linux-${KERNEL_VERSION}.tar.xz" "${KERNEL_URL}"
    tar xf "linux-${KERNEL_VERSION}.tar.xz"
fi

if [[ ! -f "${kernel_src}/arch/x86/boot/bzImage" ]]; then
    echo "[ICM-OS] Configuring and building kernel (tinyconfig + minimal drivers)..."
    cd "${kernel_src}"
    make tinyconfig
    # Minimal options for bootable system with initramfs
    cat >> .config << 'KERNEL_EOF'
CONFIG_BLK_DEV_INITRD=y
CONFIG_BLK_DEV_RAM=y
CONFIG_BLK_DEV_RAM_SIZE=65536
CONFIG_DEVTMPFS=y
CONFIG_DEVTMPFS_MOUNT=y
CONFIG_TTY=y
CONFIG_VT=y
CONFIG_SERIAL_8250=y
CONFIG_SERIAL_8250_CONSOLE=y
CONFIG_EXT4_FS=y
CONFIG_SQUASHFS=y
CONFIG_ISO9660_FS=y
CONFIG_LOOP=y
CONFIG_PROC_FS=y
CONFIG_SYSFS=y
CONFIG_64BIT=y
CONFIG_EMBEDDED=y
CONFIG_PRINTK=y
CONFIG_ELF_CORE=y
CONFIG_CGROUPS=n
CONFIG_NET=n
KERNEL_EOF
    make olddefconfig
    make -j"$(nproc)" bzImage
    cd "${BUILD_DIR}"
fi

KERNEL_BZIMAGE="${kernel_src}/arch/x86/boot/bzImage"

# --- 3) Download and build busybox ---
busybox_src="${BUILD_DIR}/busybox-${BUSYBOX_VERSION}"
if [[ ! -d "${busybox_src}" ]]; then
    echo "[ICM-OS] Downloading busybox ${BUSYBOX_VERSION}..."
    wget -q -O "busybox-${BUSYBOX_VERSION}.tar.bz2" "${BUSYBOX_URL}"
    tar xf "busybox-${BUSYBOX_VERSION}.tar.bz2"
fi

if [[ ! -f "${busybox_src}/busybox" ]]; then
    echo "[ICM-OS] Building busybox..."
    cd "${busybox_src}"
    make defconfig
    sed -i 's/# CONFIG_STATIC is not set/CONFIG_STATIC=y/' .config
    make -j"$(nproc)"
    make CONFIG_PREFIX="${BUILD_DIR}/busybox_install" install
    cd "${BUILD_DIR}"
fi

# --- 4) Build initramfs ---
echo "[ICM-OS] Building initramfs..."
rm -rf "${INITRAMFS_DIR}"
mkdir -p "${INITRAMFS_DIR}"/{bin,sbin,dev,proc,sys,usr/bin,icm-os}

# Busybox binaries
cp -a "${BUILD_DIR}/busybox_install/bin/"* "${INITRAMFS_DIR}/bin/" 2>/dev/null || true
for l in sh ash mount umount poweroff reboot; do
    ln -sf busybox "${INITRAMFS_DIR}/bin/$l" 2>/dev/null || true
done
ln -sf ../bin/busybox "${INITRAMFS_DIR}/sbin/init" 2>/dev/null || true

# Init script (PID 1)
cp "${ICM_OS_ROOT}/iso-build/initramfs/init" "${INITRAMFS_DIR}/init"
chmod +x "${INITRAMFS_DIR}/init"

# ICM-OS runtime: copy project dirs and icm_shell
echo "[ICM-OS] Copying ICM-OS runtime..."
for d in ams core primitives security gbt; do
    [[ -d "${ICM_OS_ROOT}/${d}" ]] && cp -a "${ICM_OS_ROOT}/${d}" "${INITRAMFS_DIR}/icm-os/"
done
for f in cli.py main.py requirements.txt; do
    [[ -f "${ICM_OS_ROOT}/${f}" ]] && cp -a "${ICM_OS_ROOT}/${f}" "${INITRAMFS_DIR}/icm-os/"
done
[[ -f "${ICM_OS_ROOT}/iso-build/icm_shell.py" ]] && cp "${ICM_OS_ROOT}/iso-build/icm_shell.py" "${INITRAMFS_DIR}/icm-os/icm_shell.py"

# Optional: bundle Python and minimal deps for intent shell
if command -v python3 &>/dev/null; then
    echo "[ICM-OS] Bundling Python and minimal deps for icm_shell..."
    PY_DEST="${INITRAMFS_DIR}/usr"
    mkdir -p "${PY_DEST}/bin" "${PY_DEST}/lib"
    PYTHON=$(command -v python3)
    cp -L "$PYTHON" "${PY_DEST}/bin/python3" 2>/dev/null || true
    if [[ -f "${PY_DEST}/bin/python3" ]]; then
        while read -r lib; do
            [[ -z "$lib" ]] && continue
            mkdir -p "${PY_DEST}/lib"
            cp -L "$lib" "${PY_DEST}/lib/$(basename "$lib")" 2>/dev/null || true
        done < <(ldd "${PY_DEST}/bin/python3" 2>/dev/null | awk '/=> \// { print $3 }')
        pip3 install --target="${INITRAMFS_DIR}/icm-os/deps" --quiet \
            networkx openai requests python-dotenv 2>/dev/null || true
    fi
fi

# Create initramfs cpio
INITRD="${BUILD_DIR}/initrd.img"
( cd "${INITRAMFS_DIR}" && find . | cpio -o -H newc ) | gzip -9 > "${INITRD}"
echo "[ICM-OS] Initramfs size: $(du -h "${INITRD}" | cut -f1)"

# --- 5) Create ISO with GRUB ---
echo "[ICM-OS] Creating ISO layout..."
rm -rf "${ISO_DIR}"
mkdir -p "${ISO_DIR}/boot/grub"
cp "${KERNEL_BZIMAGE}" "${ISO_DIR}/boot/vmlinuz"
cp "${INITRD}" "${ISO_DIR}/boot/initrd.img"
cp "${ICM_OS_ROOT}/iso-build/grub/grub.cfg" "${ISO_DIR}/boot/grub/grub.cfg"

echo "[ICM-OS] Running grub-mkrescue..."
grub-mkrescue -o "${OUTPUT_ISO}" "${ISO_DIR}" -- -volid ICM-OS 2>/dev/null || \
grub-mkrescue -o "${OUTPUT_ISO}" "${ISO_DIR}"

echo "[ICM-OS] Done. ISO: ${OUTPUT_ISO}"
echo "[ICM-OS] Test: qemu-system-x86_64 -cdrom ${OUTPUT_ISO} -m 512M"
