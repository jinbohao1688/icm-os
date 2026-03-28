#include "http_get.h"

#include <errno.h>
#include <netdb.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <sys/types.h>
#include <unistd.h>

#define RAW_CAP (64U * 1024U)

static void http_result_clear(HttpResult *result) {
    if (result == NULL) {
        return;
    }
    result->status_code = 0;
    result->body[0] = '\0';
    result->body_size = 0;
    result->headers[0] = '\0';
    result->error[0] = '\0';
    result->status = ICM_OK;
}

/**
 * Parse http://host[:port][/path] — supports optional IPv6 host as [addr].
 * Returns 0 on success.
 */
static int parse_http_url(const char *url, char *host, size_t host_sz, char *port,
                          size_t port_sz, char *path, size_t path_sz) {
    const char *u;
    const char *slash;
    const char *host_end;
    char hostport[512];
    size_t hostport_len;
    const char *colon;
    const char *bracket_end;

    if (url == NULL || host == NULL || port == NULL || path == NULL) {
        return -1;
    }
    if (strncmp(url, "http://", 7) != 0) {
        return -1;
    }
    u = url + 7;
    slash = strchr(u, '/');
    host_end = slash ? slash : (u + strlen(u));
    hostport_len = (size_t)(host_end - u);
    if (hostport_len == 0U || hostport_len >= sizeof hostport) {
        return -1;
    }
    (void)memcpy(hostport, u, hostport_len);
    hostport[hostport_len] = '\0';

    if (slash != NULL) {
        size_t pl = strlen(slash);
        if (pl >= path_sz) {
            return -1;
        }
        (void)memcpy(path, slash, pl + 1U);
    } else {
        if (path_sz < 2U) {
            return -1;
        }
        path[0] = '/';
        path[1] = '\0';
    }

    if (hostport[0] == '[') {
        bracket_end = strchr(hostport, ']');
        if (bracket_end == NULL) {
            return -1;
        }
        {
            size_t hl = (size_t)(bracket_end - hostport - 1U);
            if (hl >= host_sz) {
                return -1;
            }
            (void)memcpy(host, hostport + 1, hl);
            host[hl] = '\0';
        }
        if (bracket_end[1] == ':') {
            if (strlen(bracket_end + 2) >= port_sz) {
                return -1;
            }
            (void)snprintf(port, port_sz, "%s", bracket_end + 2);
        } else {
            if (port_sz < 3U) {
                return -1;
            }
            (void)memcpy(port, "80", 3);
        }
    } else {
        colon = strchr(hostport, ':');
        if (colon != NULL) {
            size_t hl = (size_t)(colon - hostport);
            if (hl >= host_sz) {
                return -1;
            }
            (void)memcpy(host, hostport, hl);
            host[hl] = '\0';
            if (strlen(colon + 1) >= port_sz) {
                return -1;
            }
            (void)snprintf(port, port_sz, "%s", colon + 1);
        } else {
            if (strlen(hostport) >= host_sz) {
                return -1;
            }
            (void)snprintf(host, host_sz, "%s", hostport);
            if (port_sz < 3U) {
                return -1;
            }
            (void)memcpy(port, "80", 3);
        }
    }
    return 0;
}

static int apply_timeouts(int fd, int timeout_sec) {
    struct timeval tv;

    if (timeout_sec <= 0) {
        return 0;
    }
    tv.tv_sec = timeout_sec;
    tv.tv_usec = 0;
    if (setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, (socklen_t)sizeof tv) != 0) {
        return -1;
    }
    if (setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &tv, (socklen_t)sizeof tv) != 0) {
        return -1;
    }
    return 0;
}

static void parse_response(const char *raw, size_t raw_len, HttpResult *result) {
    const char *p;
    const char *header_end;
    size_t header_len;
    size_t body_off;
    size_t body_len;
    char line_buf[256];
    int code = 0;

    if (raw_len == 0U) {
        result->status = ICM_ERR;
        (void)snprintf(result->error, sizeof result->error, "empty response");
        return;
    }

    p = raw;
    while ((size_t)(p - raw) < raw_len && (*p == ' ' || *p == '\t' || *p == '\r' || *p == '\n')) {
        p++;
    }

    {
        const char *line_end = strstr(p, "\r\n");
        size_t line_len;
        if (line_end == NULL) {
            line_end = strstr(p, "\n");
        }
        if (line_end == NULL) {
            result->status = ICM_ERR;
            (void)snprintf(result->error, sizeof result->error, "malformed status line");
            return;
        }
        line_len = (size_t)(line_end - p);
        if (line_len >= sizeof line_buf) {
            line_len = sizeof line_buf - 1U;
        }
        (void)memcpy(line_buf, p, line_len);
        line_buf[line_len] = '\0';
        if (sscanf(line_buf, "%*s %d", &code) != 1) {
            code = 0;
        }
        result->status_code = code;
    }

    header_end = strstr(raw, "\r\n\r\n");
    if (header_end == NULL) {
        header_end = strstr(raw, "\n\n");
        if (header_end == NULL) {
            result->status = ICM_ERR;
            (void)snprintf(result->error, sizeof result->error, "no header/body separator");
            return;
        }
        body_off = (size_t)(header_end - raw) + 2U;
    } else {
        body_off = (size_t)(header_end - raw) + 4U;
    }

    header_len = (header_end - raw);
    if (header_len >= sizeof result->headers) {
        header_len = sizeof result->headers - 1U;
    }
    (void)memcpy(result->headers, raw, header_len);
    result->headers[header_len] = '\0';

    body_len = raw_len > body_off ? (raw_len - body_off) : 0U;
    if (body_len > sizeof result->body - 1U) {
        body_len = sizeof result->body - 1U;
    }
    (void)memcpy(result->body, raw + body_off, body_len);
    result->body[body_len] = '\0';
    result->body_size = body_len;
}

void icm_http_get(const char *url, int timeout_sec, HttpResult *result) {
    static char raw[RAW_CAP];
    char host[256];
    char port[16];
    char path[1024];
    struct addrinfo hints;
    struct addrinfo *res = NULL;
    struct addrinfo *rp;
    int sockfd = -1;
    char req[2048];
    int req_len;
    ssize_t n;
    size_t total;
    int gai_err;

    http_result_clear(result);
    if (url == NULL || result == NULL) {
        if (result != NULL) {
            result->status = ICM_ERR;
            (void)snprintf(result->error, sizeof result->error, "invalid argument");
        }
        printf("[HTTP_GET] invalid argument\n");
        return;
    }

    if (parse_http_url(url, host, sizeof host, port, sizeof port, path, sizeof path) != 0) {
        result->status = ICM_ERR;
        (void)snprintf(result->error, sizeof result->error, "invalid or unsupported URL (need http://)");
        printf("[HTTP_GET] parse failed url=%.80s\n", url);
        return;
    }

    (void)memset(&hints, 0, sizeof hints);
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;

    gai_err = getaddrinfo(host, port, &hints, &res);
    if (gai_err != 0) {
        result->status = ICM_ERR;
        (void)snprintf(result->error, sizeof result->error, "getaddrinfo: %s", gai_strerror(gai_err));
        printf("[HTTP_GET] getaddrinfo failed host=%s: %s\n", host, result->error);
        return;
    }

    for (rp = res; rp != NULL; rp = rp->ai_next) {
        sockfd = socket(rp->ai_family, rp->ai_socktype, rp->ai_protocol);
        if (sockfd < 0) {
            continue;
        }
        if (apply_timeouts(sockfd, timeout_sec) != 0) {
            (void)close(sockfd);
            sockfd = -1;
            continue;
        }
        if (connect(sockfd, rp->ai_addr, rp->ai_addrlen) == 0) {
            break;
        }
        (void)close(sockfd);
        sockfd = -1;
    }
    freeaddrinfo(res);
    res = NULL;

    if (sockfd < 0) {
        result->status = ICM_ERR;
        (void)snprintf(result->error, sizeof result->error, "connect failed: %s", strerror(errno));
        printf("[HTTP_GET] connect failed host=%s port=%s\n", host, port);
        return;
    }

    req_len = snprintf(req, sizeof req,
                       "GET %s HTTP/1.1\r\n"
                       "Host: %s\r\n"
                       "User-Agent: icm-http-get/1.0\r\n"
                       "Connection: close\r\n"
                       "\r\n",
                       path, host);
    if (req_len < 0 || (size_t)req_len >= sizeof req) {
        result->status = ICM_ERR;
        (void)snprintf(result->error, sizeof result->error, "request too long");
        (void)close(sockfd);
        printf("[HTTP_GET] request buffer overflow\n");
        return;
    }

    n = send(sockfd, req, (size_t)req_len, 0);
    if (n < 0 || (size_t)n != (size_t)req_len) {
        result->status = ICM_ERR;
        (void)snprintf(result->error, sizeof result->error, "send: %s", strerror(errno));
        (void)close(sockfd);
        printf("[HTTP_GET] send failed\n");
        return;
    }

    total = 0U;
    while (total < sizeof raw - 1U) {
        n = recv(sockfd, raw + total, sizeof raw - 1U - total, 0);
        if (n < 0) {
            result->status = ICM_ERR;
            (void)snprintf(result->error, sizeof result->error, "recv: %s", strerror(errno));
            (void)close(sockfd);
            printf("[HTTP_GET] recv error\n");
            return;
        }
        if (n == 0) {
            break;
        }
        total += (size_t)n;
    }
    raw[total] = '\0';
    (void)close(sockfd);
    sockfd = -1;

    parse_response(raw, total, result);
    if (result->status == ICM_OK) {
        printf("[HTTP_GET] ok url=%.80s code=%d body_bytes=%zu\n", url, result->status_code,
               result->body_size);
    } else {
        printf("[HTTP_GET] parse error url=%.80s: %s\n", url, result->error);
    }
}

