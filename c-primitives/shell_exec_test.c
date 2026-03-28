#include "shell_exec.h"

#include <stdio.h>
#include <string.h>

static void dump(const char *label, const IcmResult *r) {
    printf("[%s] status=%d size=%zu\n", label, r->status, r->size);
    if (r->error[0] != '\0') {
        printf("[%s] error: %s\n", label, r->error);
    }
    if (r->size > 0U) {
        printf("[%s] output:\n%.*s\n", label, (int)r->size, r->data);
    }
}

int main(void) {
    IcmResult r;

    printf("=== icm_shell_exec tests ===\n\n");

    printf("1) echo hello from C\n");
    icm_shell_exec("echo hello from C", 0, &r);
    dump("echo", &r);
    if (r.status != 0 || strstr(r.data, "hello from C") == NULL) {
        printf("FAIL: echo\n");
        return 1;
    }

    printf("\n2) ls /tmp\n");
    icm_shell_exec("ls /tmp", 0, &r);
    dump("ls", &r);
    if (r.status != 0) {
        printf("FAIL: ls exit code\n");
        return 1;
    }

    printf("\n3) sleep 10 with timeout 2\n");
    icm_shell_exec("sleep 10", 2, &r);
    dump("timeout", &r);
    if (strstr(r.error, "timed out") == NULL) {
        printf("FAIL: expected timeout error message\n");
        return 1;
    }
    if (r.status != 128 + 9) {
        printf("FAIL: expected status 137 (SIGKILL), got %d\n", r.status);
        return 1;
    }

    printf("\n4) nonexistent command\n");
    icm_shell_exec("/nonexistent/path/icm_no_such_binary_zz", 0, &r);
    dump("nox", &r);
    if (r.status != 127) {
        printf("FAIL: expected exit 127 from sh, got %d\n", r.status);
        return 1;
    }

    printf("\n=== ALL SHELL_EXEC TESTS PASSED ===\n");
    return 0;
}
