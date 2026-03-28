#ifndef ICM_DNS_RESOLVE_H
#define ICM_DNS_RESOLVE_H

#include "file_primitive.h"

/**
 * DNS resolution result (TTL is a fixed placeholder; getaddrinfo does not return TTL).
 */
typedef struct {
    char ip[64];
    int ttl;
    char domain[256];
    char error[256];
    int status;
} DnsResult;

/**
 * Resolve `domain` to an IP string using getaddrinfo (IPv4 or IPv6).
 * On success: result->status == ICM_OK, first address in result->ip, result->ttl == 300.
 * On failure: result->status == ICM_ERR, message in result->error.
 */
void icm_dns_resolve(const char *domain, DnsResult *result);

#endif /* ICM_DNS_RESOLVE_H */
