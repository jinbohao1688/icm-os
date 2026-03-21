#!/bin/bash
set -e
ICMOS_DIR=~/icm-os
INITRD_DIR=/tmp/icm_root
INITRD_OUT=$ICMOS_DIR/iso-build/work/initrd.img

echo "[ICM-OS] 重建 initramfs..."
rm -rf $INITRD_DIR
mkdir -p $INITRD_DIR/{bin,dev,proc,sys,root,etc,usr/bin,usr/lib/python3.10,icm-os/deps,lib/x86_64-linux-gnu,lib64}

cp $ICMOS_DIR/iso-build/work/busybox_install/bin/busybox $INITRD_DIR/bin/
cd $INITRD_DIR/bin
for cmd in sh ls cat mount echo ps free mkdir; do ln -sf busybox $cmd 2>/dev/null; done
cd $ICMOS_DIR

cp /usr/sbin/ip $INITRD_DIR/bin/ip
for lib in $(ldd /usr/sbin/ip | grep "=> /" | awk '{print $3}'); do
    cp "$lib" $INITRD_DIR/lib/x86_64-linux-gnu/ 2>/dev/null
done

cp /usr/bin/python3.10 $INITRD_DIR/usr/bin/python3
cp -r /usr/lib/python3.10 $INITRD_DIR/usr/lib/
rm -rf $INITRD_DIR/usr/lib/python3.10/test 2>/dev/null

for lib in libm.so.6 libexpat.so.1 libz.so.1 libc.so.6 libbz2.so.1.0 liblzma.so.5 libreadline.so.8 libtinfo.so.6 libgcc_s.so.1 libssl.so.3 libcrypto.so.3 libffi.so.8 libpthread.so.0; do
    find /lib /usr/lib -name "$lib" 2>/dev/null | head -1 | xargs -I{} cp {} $INITRD_DIR/lib/x86_64-linux-gnu/ 2>/dev/null
done
cp /usr/lib/x86_64-linux-gnu/librt.so.1 $INITRD_DIR/lib/x86_64-linux-gnu/
cp /usr/lib/x86_64-linux-gnu/libdl.so.2 $INITRD_DIR/lib/x86_64-linux-gnu/
cp /lib64/ld-linux-x86-64.so.2 $INITRD_DIR/lib64/

cp -r $ICMOS_DIR/ams $ICMOS_DIR/core $ICMOS_DIR/primitives $ICMOS_DIR/security $ICMOS_DIR/gbt $INITRD_DIR/icm-os/
cp $ICMOS_DIR/iso-build/icm_shell.py $INITRD_DIR/icm-os/
cp $ICMOS_DIR/.env $INITRD_DIR/icm-os/ 2>/dev/null
pip3 install --target=$INITRD_DIR/icm-os/deps networkx openai requests python-dotenv 2>&1 | tail -2
echo "nameserver 8.8.8.8" > $INITRD_DIR/etc/resolv.conf

cat > /tmp/init.c << 'EOF'
#include <unistd.h>
#include <sys/mount.h>
#include <stdio.h>
int main() {
    mount("proc","/proc","proc",0,NULL);
    mount("sysfs","/sys","sysfs",0,NULL);
    mount("devtmpfs","/dev","devtmpfs",0,NULL);
    printf("\n  ICM-OS v0.1\n\n");
    char *envp[]={"PATH=/bin:/sbin:/usr/bin","PYTHONPATH=/icm-os:/icm-os/deps","HOME=/root","TERM=linux","LD_LIBRARY_PATH=/lib/x86_64-linux-gnu:/lib64",NULL};
    while(1){
        char *py[]={"/usr/bin/python3","/icm-os/icm_shell.py",NULL};
        execve("/usr/bin/python3",py,envp);
        char *sh[]={"/bin/sh",NULL};
        execve("/bin/sh",sh,envp);
        sleep(1);
    }
}
EOF
gcc -static -o $INITRD_DIR/init /tmp/init.c

echo "[ICM-OS] 打包..."
cd $INITRD_DIR
find . | cpio -o -H newc | gzip > $INITRD_OUT
echo "[ICM-OS] 完成！$(du -sh $INITRD_OUT | cut -f1)"
