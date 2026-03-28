#include "http_get.h"

#include <stdio.h>
#include <string.h>

static void dump(const char *label, const HttpResult *r) {
    printf("[%s] status=%d http_code=%d body_size=%zu\n", label, r->status, r->status_code,
           r->body_size);
    if (r->error[0] != '\0') {
        printf("[%s] error: %s\n", label, r->error);
    }
    if (r->headers[0] != '\0') {
        printf("[%s] headers (first 120 chars): %.120s...\n", label, r->headers);
    }
    if (r->body_size > 0U) {
        printf("[%s] body (first 200 chars):\n%.*s\n", label, 200, r->body);
    }
}

int main(void) {
    HttpResult r;

    printf("=== icm_http_get tests ===\n\n");

    printf("1) GET http://example.com/\n");
    icm_http_get("http://example.com/", 10, &r);
    dump("example", &r);
    if (r.status != ICM_OK || r.status_code != 200) {
        printf("FAIL: example.com (want ICM_OK and HTTP 200)\n");
        return 1;
    }

    printf("\n2) GET http://httpbin.org/ip\n");
    icm_http_get("http://httpbin.org/ip", 20, &r);
    dump("httpbin", &r);
    if (r.status != ICM_OK || r.status_code != 200) {
        printf("FAIL: httpbin (want ICM_OK and HTTP 200)\n");
        return 1;
    }
    if (strstr(r.body, "origin") == NULL) {
        printf("FAIL: httpbin body should mention origin\n");
        return 1;
    }

    printf("\n3) nonexistent host\n");
    icm_http_get("http://icm-nonexistent-host-zzzz.invalid/", 5, &r);
    dump("nx", &r);
    if (r.status != ICM_ERR) {
        printf("FAIL: expected ICM_ERR for bad host\n");
        return 1;
    }

    printf("\n=== ALL HTTP_GET TESTS PASSED ===\n");
    return 0;
}
