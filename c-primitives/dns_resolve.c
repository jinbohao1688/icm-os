#include "dns_resolve.h"

#include <arpa/inet.h>
#include <errno.h>
#include <netdb.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>

static void result_clear(DnsResult *result) {
    if (result == NULL) {
        return;
    }
    result->ip[0] = '\0';
    result->ttl = 0;
    result->domain[0] = '\0';
    result->error[0] = '\0';
    result->status = ICM_OK;
}

void icm_dns_resolve(const char *domain, DnsResult *result) {
    struct addrinfo hints;
    struct addrinfo *res = NULL;
    int gai;
    const void *addrptr = NULL;
    int af = AF_UNSPEC;

    result_clear(result);
    if (domain == NULL || result == NULL) {
        if (result != NULL) {
            result->status = ICM_ERR;
            (void)snprintf(result->error, sizeof result->error, "invalid argument");
        }
        printf("[DNS_RESOLVE] invalid argument\n");
        return;
    }

    (void)memset(&hints, 0, sizeof hints);
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;

    gai = getaddrinfo(domain, NULL, &hints, &res);
    if (gai != 0) {
        result->status = ICM_ERR;
        (void)snprintf(result->error, sizeof result->error, "%s", gai_strerror(gai));
        printf("[DNS_RESOLVE] getaddrinfo failed domain=%s: %s\n", domain, result->error);
        return;
    }

    if (res == NULL) {
        result->status = ICM_ERR;
        (void)snprintf(result->error, sizeof result->error, "no addresses returned");
        printf("[DNS_RESOLVE] empty result for domain=%s\n", domain);
        return;
    }

    if (res->ai_family == AF_INET) {
        af = AF_INET;
        addrptr = (const void *)&((const struct sockaddr_in *)(void *)res->ai_addr)->sin_addr;
    } else if (res->ai_family == AF_INET6) {
        af = AF_INET6;
        addrptr = (const void *)&((const struct sockaddr_in6 *)(void *)res->ai_addr)->sin6_addr;
    } else {
        result->status = ICM_ERR;
        (void)snprintf(result->error, sizeof result->error, "unsupported address family");
        printf("[DNS_RESOLVE] unsupported ai_family for domain=%s\n", domain);
        freeaddrinfo(res);
        return;
    }

    if (inet_ntop(af, addrptr, result->ip, sizeof result->ip) == NULL) {
        result->status = ICM_ERR;
        (void)snprintf(result->error, sizeof result->error, "inet_ntop: %s", strerror(errno));
        printf("[DNS_RESOLVE] inet_ntop failed domain=%s: %s\n", domain, result->error);
        freeaddrinfo(res);
        return;
    }

    (void)snprintf(result->domain, sizeof result->domain, "%s", domain);
    result->ttl = 300;
    result->status = ICM_OK;

    freeaddrinfo(res);
    printf("[DNS_RESOLVE] ok domain=%s ip=%s ttl=%d (placeholder)\n", domain, result->ip,
           result->ttl);
}
