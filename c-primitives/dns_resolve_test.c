#include "dns_resolve.h"

#include <stdio.h>
#include <string.h>

static void dump(const char *label, const DnsResult *r) {
    printf("[%s] status=%d ip=%s ttl=%d domain=%s\n", label, r->status, r->ip, r->ttl,
           r->domain);
    if (r->error[0] != '\0') {
        printf("[%s] error: %s\n", label, r->error);
    }
}

int main(void) {
    DnsResult r;

    printf("=== icm_dns_resolve tests ===\n\n");

    printf("1) google.com\n");
    icm_dns_resolve("google.com", &r);
    dump("google", &r);
    if (r.status != ICM_OK || r.ip[0] == '\0') {
        printf("FAIL: google.com\n");
        return 1;
    }

    printf("\n2) github.com\n");
    icm_dns_resolve("github.com", &r);
    dump("github", &r);
    if (r.status != ICM_OK || r.ip[0] == '\0') {
        printf("FAIL: github.com\n");
        return 1;
    }

    printf("\n3) nonexistent domain\n");
    icm_dns_resolve("this-domain-should-not-exist-icm.invalid", &r);
    dump("nx", &r);
    if (r.status != ICM_ERR) {
        printf("FAIL: expected ICM_ERR for bogus domain, got status=%d\n", r.status);
        return 1;
    }
    if (r.error[0] == '\0') {
        printf("FAIL: expected error message\n");
        return 1;
    }

    printf("\n=== ALL DNS_RESOLVE TESTS PASSED ===\n");
    return 0;
}
