#!/bin/bash
set -e
ICMOS_DIR="${ICMOS_DIR:-$HOME/icm-os}"
INITRD_DIR=/tmp/icm_root
INITRD_OUT="$ICMOS_DIR/iso-build/work/initrd.img"

echo "[ICM-OS] 重建 initramfs..."
rm -rf "$INITRD_DIR"
mkdir -p "$INITRD_DIR"/{bin,dev,proc,sys,root,etc,usr/bin,usr/lib/python3.10,icm-os/deps,lib/x86_64-linux-gnu,lib64}

cp "$ICMOS_DIR/iso-build/work/busybox_install/bin/busybox" "$INITRD_DIR/bin/"
cd "$INITRD_DIR/bin"
for cmd in sh ls cat mount echo ps free mkdir; do ln -sf busybox "$cmd" 2>/dev/null; done
cd "$ICMOS_DIR"

cp /usr/sbin/ip "$INITRD_DIR/bin/ip"
for lib in $(ldd /usr/sbin/ip | grep "=> /" | awk '{print $3}'); do
    cp "$lib" "$INITRD_DIR/lib/x86_64-linux-gnu/" 2>/dev/null || true
done

cp /usr/bin/python3.10 "$INITRD_DIR/usr/bin/python3"
cp -r /usr/lib/python3.10 "$INITRD_DIR/usr/lib/"
rm -rf "$INITRD_DIR/usr/lib/python3.10/test" 2>/dev/null || true

for lib in libm.so.6 libexpat.so.1 libz.so.1 libc.so.6 libbz2.so.1.0 liblzma.so.5 libreadline.so.8 libtinfo.so.6 libgcc_s.so.1 libssl.so.3 libcrypto.so.3 libffi.so.8 libpthread.so.0; do
    find /lib /usr/lib -name "$lib" 2>/dev/null | head -1 | xargs -I{} cp {} "$INITRD_DIR/lib/x86_64-linux-gnu/" 2>/dev/null || true
done
cp /usr/lib/x86_64-linux-gnu/librt.so.1 "$INITRD_DIR/lib/x86_64-linux-gnu/" 2>/dev/null || true
cp /usr/lib/x86_64-linux-gnu/libdl.so.2 "$INITRD_DIR/lib/x86_64-linux-gnu/" 2>/dev/null || true
cp /lib64/ld-linux-x86-64.so.2 "$INITRD_DIR/lib64/" 2>/dev/null || true

cp -r "$ICMOS_DIR/ams" "$ICMOS_DIR/core" "$ICMOS_DIR/primitives" "$ICMOS_DIR/security" "$ICMOS_DIR/gbt" "$INITRD_DIR/icm-os/"
cp "$ICMOS_DIR/iso-build/icm_shell.py" "$INITRD_DIR/icm-os/"
cp "$ICMOS_DIR/.env" "$INITRD_DIR/icm-os/" 2>/dev/null || true
pip3 install --target="$INITRD_DIR/icm-os/deps" networkx openai requests python-dotenv beautifulsoup4 2>&1 | tail -2
echo "nameserver 8.8.8.8" > "$INITRD_DIR/etc/resolv.conf"

# --- C 版 icm_shell：编译并放入 initramfs ---
echo "[ICM-OS] 构建 c-primitives/icm_shell..."
make -C "$ICMOS_DIR/c-primitives" icm_shell
ICM_SHELL_BIN="$ICMOS_DIR/c-primitives/icm_shell"
if [[ ! -x "$ICM_SHELL_BIN" ]]; then
    echo "[ICM-OS] ERROR: $ICM_SHELL_BIN 不存在或不可执行" >&2
    exit 1
fi

echo "[ICM-OS] file icm_shell:"
file "$ICM_SHELL_BIN" || true

if file "$ICM_SHELL_BIN" 2>/dev/null | grep -qiE 'statically linked|static-pie'; then
    echo "[ICM-OS] icm_shell 为静态链接，无需复制动态库"
else
    echo "[ICM-OS] icm_shell 为动态链接，按 ldd 复制依赖库..."
    while read -r lib; do
        [[ -z "$lib" ]] && continue
        [[ -f "$lib" ]] && cp -L "$lib" "$INITRD_DIR/lib/x86_64-linux-gnu/" 2>/dev/null || true
    done < <(ldd "$ICM_SHELL_BIN" 2>/dev/null | awk '/=> \// {print $3}')
fi

cp "$ICM_SHELL_BIN" "$INITRD_DIR/bin/icm_shell"
chmod +x "$INITRD_DIR/bin/icm_shell"

cat > /tmp/init.c << 'CEOF'
#include <unistd.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    mount("proc", "/proc", "proc", 0, NULL);
    mount("sysfs", "/sys", "sysfs", 0, NULL);
    mount("devtmpfs", "/dev", "devtmpfs", 0, NULL);
    mount("tmpfs", "/data", "tmpfs", 0, "size=64m");
    mkdir("/data/config", 0755);
    mkdir("/data/notes", 0755);
    mkdir("/data/history", 0755);
    mkdir("/data/primitives", 0755);
    mkdir("/etc", 0755);
    {
        FILE *f = fopen("/etc/resolv.conf", "w");
        if (f) {
            fprintf(f, "nameserver 8.8.8.8\n");
            fclose(f);
        }
    }
    printf("  [storage] /data ready\n");
    system("/bin/ip link set eth0 up 2>/dev/null");
    system("/bin/ip addr add 10.0.2.15/24 dev eth0 2>/dev/null");
    system("/bin/ip route add default via 10.0.2.2 2>/dev/null");
    printf("  [network] eth0 ready (10.0.2.15)\n");
    printf("\n  ICM-OS v0.1\n\n");

    char *envp[] = {
        "PATH=/bin:/sbin:/usr/bin",
        "PYTHONPATH=/icm-os:/icm-os/deps",
        "HOME=/root",
        "TERM=linux",
        "LD_LIBRARY_PATH=/lib/x86_64-linux-gnu:/lib64",
        "ICM_PRIMITIVE_CACHE=/data/primitives",
        NULL
    };

    for (;;) {
        char *icm[] = { "/bin/icm_shell", NULL };
        execve("/bin/icm_shell", icm, envp);
        char *py[] = { "/usr/bin/python3", "/icm-os/icm_shell.py", NULL };
        execve("/usr/bin/python3", py, envp);
        char *sh[] = { "/bin/sh", NULL };
        execve("/bin/sh", sh, envp);
        sleep(1);
    }
}
CEOF

gcc -static -o "$INITRD_DIR/init" /tmp/init.c

# 复制已缓存的动态原语
PRIMITIVE_CACHE="${HOME}/.icm-os/primitives"
if [[ -d "$PRIMITIVE_CACHE" ]] && [[ -n "$(ls -A "$PRIMITIVE_CACHE" 2>/dev/null)" ]]; then
    mkdir -p "$INITRD_DIR/data/primitives"
    cp "$PRIMITIVE_CACHE"/*.py "$INITRD_DIR/data/primitives/" 2>/dev/null || true
    echo "[ICM-OS] Bundled $(ls "$PRIMITIVE_CACHE"/*.py 2>/dev/null | wc -l) cached primitives"
fi

echo "[ICM-OS] 打包..."
cd "$INITRD_DIR"
find . | cpio -o -H newc | gzip > "$INITRD_OUT"
echo "[ICM-OS] 完成！$(du -sh "$INITRD_OUT" | cut -f1)"
