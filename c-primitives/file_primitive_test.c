#include "file_primitive.h"

#include <stdio.h>
#include <string.h>

static void print_result(const char *step, const IcmResult *r) {
    printf("[%s] status=%d size=%zu\n", step, r->status, r->size);
    if (r->status != ICM_OK && r->error[0] != '\0') {
        printf("[%s] error: %s\n", step, r->error);
    }
    if (r->size > 0U && r->data[0] != '\0') {
        printf("[%s] data (preview up to 200 chars):\n%.*s\n", step, 200, r->data);
    }
}

int main(void) {
    IcmResult r;
    const char *test_path = "/tmp/icm_test.txt";
    const char *payload = "ICM-OS C primitive test line\n";

    printf("=== ICM file primitive tests ===\n\n");

    printf("1) Write %s\n", test_path);
    if (icm_file_write(test_path, payload, "w") != ICM_OK) {
        printf("TEST FAIL: write returned error\n");
        return 1;
    }

    printf("\n2) Read back\n");
    icm_file_read(test_path, &r);
    print_result("read", &r);
    if (r.status != ICM_OK) {
        printf("TEST FAIL: read status\n");
        return 1;
    }
    if (r.size != strlen(payload) || strcmp(r.data, payload) != 0) {
        printf("TEST FAIL: content mismatch (expected len %zu got %zu)\n",
               strlen(payload), r.size);
        return 1;
    }

    printf("\n3) List /tmp (snippet)\n");
    icm_file_list("/tmp", &r);
    print_result("list", &r);
    if (r.status != ICM_OK) {
        printf("TEST FAIL: list status\n");
        return 1;
    }
    if (strstr(r.data, "icm_test.txt") == NULL) {
        printf("TEST FAIL: icm_test.txt not found in listing\n");
        return 1;
    }

    printf("\n=== ALL TESTS PASSED ===\n");
    return 0;
}
