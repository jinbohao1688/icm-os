/*
 * ICM-OS C shell — keyword intents + optional AMS (DeepSeek) decomposition.
 */

#ifndef _POSIX_C_SOURCE
#define _POSIX_C_SOURCE 200809L
#endif

#include "ams.h"
#include "dns_resolve.h"
#include "file_primitive.h"
#include "http_get.h"
#include "shell_exec.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>

#define LINE_MAX 8192

static char g_deepseek_key[512];

static void chomp_line(char *s) {
    size_t n;

    if (s == NULL) {
        return;
    }
    n = strlen(s);
    while (n > 0U && (s[n - 1U] == '\n' || s[n - 1U] == '\r')) {
        s[n - 1U] = '\0';
        n--;
    }
}

static void trim_inplace(char *s) {
    char *start;
    char *end;

    if (s == NULL) {
        return;
    }
    start = s;
    while (*start == ' ' || *start == '\t') {
        start++;
    }
    if (start != s) {
        (void)memmove(s, start, strlen(start) + 1U);
    }
    if (*s == '\0') {
        return;
    }
    end = s + strlen(s) - 1U;
    while (end > s && (*end == ' ' || *end == '\t')) {
        *end = '\0';
        end--;
    }
}

static void print_icm_result(const IcmResult *r, const char *label) {
    printf("[%s] exit/status=%d size=%zu\n", label, r->status, r->size);
    if (r->error[0] != '\0') {
        printf("[%s] error: %s\n", label, r->error);
    }
    if (r->size > 0U && r->data[0] != '\0') {
        printf("%s", r->data);
        if (r->size == 0U || r->data[r->size - 1U] != '\n') {
            printf("\n");
        }
    }
}

static void handle_read_file(const char *line) {
    IcmResult r;
    const char *p;
    const char *path;

    p = strstr(line, "read file");
    if (p == NULL) {
        return;
    }
    path = p + strlen("read file");
    while (*path == ' ' || *path == '\t') {
        path++;
    }
    if (*path == '\0') {
        printf("[ICM] read file: missing path\n");
        return;
    }
    icm_file_read(path, &r);
    if (r.status != ICM_OK) {
        printf("[ICM] read failed: %s\n", r.error);
        return;
    }
    printf("[ICM] read %zu bytes\n", r.size);
    (void)fwrite(r.data, 1U, r.size, stdout);
    if (r.size == 0U || r.data[r.size - 1U] != '\n') {
        printf("\n");
    }
}

static void handle_write(char *line) {
    char path[1024];
    const char *s;
    int nread;

    if (strncmp(line, "write ", 6) != 0) {
        return;
    }
    s = line + 6U;
    while (*s == ' ' || *s == '\t') {
        s++;
    }
    if (*s == '\0') {
        printf("[ICM] write: usage: write <path> <content>\n");
        return;
    }
    if (sscanf(s, "%1023s%n", path, &nread) != 1) {
        printf("[ICM] write: bad path\n");
        return;
    }
    s += (size_t)nread;
    while (*s == ' ' || *s == '\t') {
        s++;
    }
    if (*s == '\0') {
        printf("[ICM] write: missing content\n");
        return;
    }
    if (icm_file_write(path, s, "w") == ICM_OK) {
        printf("[ICM] wrote to %s\n", path);
    } else {
        printf("[ICM] write failed\n");
    }
}

static void handle_list(char *line) {
    IcmResult r;
    char *path;

    if (strncmp(line, "list ", 5) == 0) {
        path = line + 5;
    } else if (strncmp(line, "ls ", 3) == 0) {
        path = line + 3;
    } else if (strcmp(line, "list") == 0 || strcmp(line, "ls") == 0) {
        icm_file_list(".", &r);
        if (r.status != ICM_OK) {
            printf("[ICM] list failed: %s\n", r.error);
            return;
        }
        printf("%s", r.data);
        if (r.size == 0U || r.data[r.size - 1U] != '\n') {
            printf("\n");
        }
        return;
    } else {
        return;
    }
    trim_inplace(path);
    if (*path == '\0') {
        path = ".";
    }
    icm_file_list(path, &r);
    if (r.status != ICM_OK) {
        printf("[ICM] list failed: %s\n", r.error);
        return;
    }
    printf("%s", r.data);
    if (r.size == 0U || r.data[r.size - 1U] != '\n') {
        printf("\n");
    }
}

static void handle_dns(char *line) {
    DnsResult r;
    char domain[256];
    char *s;

    if (strncmp(line, "dns ", 4) == 0) {
        s = line + 4;
    } else if (strncmp(line, "resolve ", 8) == 0) {
        s = line + 8;
    } else {
        return;
    }
    trim_inplace(s);
    if (*s == '\0') {
        printf("[ICM] dns: missing domain\n");
        return;
    }
    if (strlen(s) >= sizeof domain) {
        printf("[ICM] dns: domain too long\n");
        return;
    }
    (void)snprintf(domain, sizeof domain, "%s", s);
    icm_dns_resolve(domain, &r);
    if (r.status != ICM_OK) {
        printf("[ICM] dns failed: %s\n", r.error);
        return;
    }
    printf("[ICM] %s -> %s (ttl=%d)\n", r.domain, r.ip, r.ttl);
}

static void handle_http(char *line) {
    HttpResult hr;
    char url[2048];
    char *s;

    if (strncmp(line, "fetch ", 6) == 0) {
        s = line + 6;
    } else if (strncmp(line, "http ", 5) == 0) {
        s = line + 5;
    } else {
        return;
    }
    trim_inplace(s);
    if (*s == '\0') {
        printf("[ICM] fetch: missing URL\n");
        return;
    }
    if (strlen(s) >= sizeof url) {
        printf("[ICM] fetch: URL too long\n");
        return;
    }
    (void)snprintf(url, sizeof url, "%s", s);
    icm_http_get(url, 30, &hr);
    if (hr.status != ICM_OK) {
        printf("[ICM] http_get failed: %s\n", hr.error);
        return;
    }
    printf("[ICM] HTTP %d\n", hr.status_code);
    if (hr.body_size > 0U) {
        size_t n = hr.body_size > 500U ? 500U : hr.body_size;
        (void)fwrite(hr.body, 1U, n, stdout);
        printf("\n");
    }
}

static const char *ams_get_param(const AmsResult *a, const char *key) {
    int i;

    if (a == NULL || key == NULL) {
        return "";
    }
    for (i = 0; i < a->param_count; i++) {
        if (strcmp(a->param_keys[i], key) == 0) {
            return a->params[i];
        }
    }
    return "";
}

static void handle_ams_primitive(const AmsResult *ar) {
    IcmResult ir;
    DnsResult dr;
    HttpResult hr;
    const char *p;
    const char *c;

    if (strcasecmp(ar->primitive_id, "DNS_RESOLVE") == 0) {
        p = ams_get_param(ar, "domain");
        if (p[0] == '\0') {
            printf("[AMS] missing domain\n");
            return;
        }
        icm_dns_resolve(p, &dr);
        if (dr.status != ICM_OK) {
            printf("[AMS] dns: %s\n", dr.error);
            return;
        }
        printf("[AMS] %s -> %s\n", p, dr.ip);
        return;
    }
    if (strcasecmp(ar->primitive_id, "HTTP_GET") == 0) {
        p = ams_get_param(ar, "url");
        if (p[0] == '\0') {
            printf("[AMS] missing url\n");
            return;
        }
        icm_http_get(p, 30, &hr);
        if (hr.status != ICM_OK) {
            printf("[AMS] http: %s\n", hr.error);
            return;
        }
        printf("[AMS] HTTP %d\n", hr.status_code);
        if (hr.body_size > 0U) {
            size_t n = hr.body_size > 500U ? 500U : hr.body_size;
            (void)fwrite(hr.body, 1U, n, stdout);
            printf("\n");
        }
        return;
    }
    if (strcasecmp(ar->primitive_id, "FILE_READ") == 0) {
        p = ams_get_param(ar, "path");
        if (p[0] == '\0') {
            printf("[AMS] missing path\n");
            return;
        }
        icm_file_read(p, &ir);
        if (ir.status != ICM_OK) {
            printf("[AMS] read: %s\n", ir.error);
            return;
        }
        (void)fwrite(ir.data, 1U, ir.size, stdout);
        printf("\n");
        return;
    }
    if (strcasecmp(ar->primitive_id, "FILE_WRITE") == 0) {
        p = ams_get_param(ar, "path");
        c = ams_get_param(ar, "content");
        if (p[0] == '\0') {
            printf("[AMS] missing path\n");
            return;
        }
        if (c[0] == '\0') {
            printf("[AMS] missing content\n");
            return;
        }
        if (icm_file_write(p, c, "w") != ICM_OK) {
            printf("[AMS] write failed\n");
            return;
        }
        printf("[AMS] wrote %s\n", p);
        return;
    }
    if (strcasecmp(ar->primitive_id, "SHELL_EXEC") == 0) {
        p = ams_get_param(ar, "command");
        if (p[0] == '\0') {
            printf("[AMS] missing command\n");
            return;
        }
        icm_shell_exec(p, 120, &ir);
        print_icm_result(&ir, "ams-exec");
        return;
    }
    if (strcasecmp(ar->primitive_id, "FILE_LIST") == 0) {
        p = ams_get_param(ar, "path");
        if (p[0] == '\0') {
            p = ".";
        }
        icm_file_list(p, &ir);
        if (ir.status != ICM_OK) {
            printf("[AMS] list: %s\n", ir.error);
            return;
        }
        printf("%s", ir.data);
        if (ir.size == 0U || ir.data[ir.size - 1U] != '\n') {
            printf("\n");
        }
        return;
    }
    printf("[AMS] unknown primitive: %s\n", ar->primitive_id);
}

static void handle_bang(const char *line) {
    IcmResult r;
    const char *cmd;

    if (line[0] != '!') {
        return;
    }
    cmd = line + 1U;
    while (*cmd == ' ' || *cmd == '\t') {
        cmd++;
    }
    if (*cmd == '\0') {
        printf("[ICM] !: empty command\n");
        return;
    }
    icm_shell_exec(cmd, 120, &r);
    print_icm_result(&r, "exec");
}

static void print_banner(void) {
    printf(
        " ___  ____ __  __       ___  ____\n"
        "|_ _|/ ___|  \\/  |     / _ \\/ ___|\n"
        " | || |   | |\\/| |____| | | \\___ \\\n"
        " | || |___| |  | |____| |_| |___) |\n"
        "|___|\\____|_|  |_|     \\___/|____/\n"
        "\n"
        " Intent-Centric Meta Operating System v0.1 (C edition)\n"
        "\n");
}

static int dispatch(char *line) {
    trim_inplace(line);
    if (*line == '\0') {
        return 0;
    }

    if (strcmp(line, "exit") == 0 || strcmp(line, "quit") == 0) {
        return 1;
    }

    if (line[0] == '!') {
        handle_bang(line);
        return 0;
    }

    if (strstr(line, "read file") != NULL) {
        handle_read_file(line);
        return 0;
    }

    if (strncmp(line, "write ", 6) == 0) {
        handle_write(line);
        return 0;
    }

    if (strncmp(line, "list ", 5) == 0 || strncmp(line, "ls ", 3) == 0 || strcmp(line, "list") == 0 ||
        strcmp(line, "ls") == 0) {
        handle_list(line);
        return 0;
    }

    if (strncmp(line, "dns ", 4) == 0 || strncmp(line, "resolve ", 8) == 0) {
        handle_dns(line);
        return 0;
    }

    if (strncmp(line, "fetch ", 6) == 0 || strncmp(line, "http ", 5) == 0) {
        handle_http(line);
        return 0;
    }

    if (g_deepseek_key[0] != '\0') {
        AmsResult ar;
        icm_ams_decompose(line, g_deepseek_key, &ar);
        if (ar.status == ICM_OK && ar.primitive_id[0] != '\0') {
            printf("[AMS] Graph: %s\n", ar.primitive_id);
            handle_ams_primitive(&ar);
            return 0;
        }
        if (ar.error[0] != '\0') {
            printf("[AMS] %s\n", ar.error);
        } else {
            printf("[ICM] Unknown intent: %s\n", line);
        }
        return 0;
    }

    printf("[ICM] Unknown intent: %s\n", line);
    return 0;
}

int main(void) {
    char line[LINE_MAX];
    const char *envk;

    g_deepseek_key[0] = '\0';
    envk = getenv("DEEPSEEK_API_KEY");
    if (envk != NULL && envk[0] != '\0') {
        (void)snprintf(g_deepseek_key, sizeof g_deepseek_key, "%s", envk);
    }

    print_banner();
    if (g_deepseek_key[0] != '\0') {
        printf(" AMS: DeepSeek decomposition enabled.\n\n");
    }
    for (;;) {
        (void)printf("icm> ");
        (void)fflush(stdout);
        if (fgets(line, (int)sizeof line, stdin) == NULL) {
            printf("\n");
            break;
        }
        chomp_line(line);
        if (dispatch(line) != 0) {
            break;
        }
    }
    return 0;
}
