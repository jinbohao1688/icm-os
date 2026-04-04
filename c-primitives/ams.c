#include "ams.h"

#include "shell_exec.h"

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define REQ_TEMPLATE_MAX (32U * 1024U)
#define CURL_CMD_MAX 8192
#define RESP_READ_MAX (64U * 1024U)

static void ams_clear(AmsResult *r) {
    size_t i;

    if (r == NULL) {
        return;
    }
    r->primitive_id[0] = '\0';
    for (i = 0U; i < (size_t)AMS_PARAM_MAX; i++) {
        r->params[i][0] = '\0';
        r->param_keys[i][0] = '\0';
    }
    r->param_count = 0;
    r->error[0] = '\0';
    r->status = ICM_OK;
}

static int json_append_escaped(const char *in, char *out, size_t outsz, size_t *pos) {
    size_t p;
    const unsigned char *u;

    if (out == NULL || pos == NULL || in == NULL) {
        return -1;
    }
    p = *pos;
    u = (const unsigned char *)in;
    while (*u != '\0') {
        if (p + 7U >= outsz) {
            return -1;
        }
        if (*u == '\\' || *u == '"') {
            out[p++] = '\\';
        }
        if (*u < 32U && *u != '\t') {
            /* skip control chars */
            u++;
            continue;
        }
        out[p++] = (char)*u;
        u++;
    }
    out[p] = '\0';
    *pos = p;
    return 0;
}

static int write_request_file(const char *intent, char *path_out, size_t path_out_sz) {
    static char body[REQ_TEMPLATE_MAX];
    size_t pos = 0U;
    const char *sys =
        "你是 ICM-OS 意图分解器。根据用户意图，返回 JSON："
        "{\"primitive\": \"PRIMITIVE_ID\", \"params\": {\"key\": \"value\"}} "
        "可用原语：DNS_RESOLVE(domain), HTTP_GET(url), FILE_READ(path), "
        "FILE_WRITE(path,content), SHELL_EXEC(command), FILE_LIST(path)。"
        "只输出 JSON，不要 Markdown，不要解释。";

    if (path_out == NULL || path_out_sz < 32U) {
        return -1;
    }
    (void)snprintf(path_out, path_out_sz, "/tmp/icm_ams_reqXXXXXX");
    {
        int fd = mkstemp(path_out);
        FILE *fp;
        if (fd < 0) {
            return -1;
        }
        fp = fdopen(fd, "w");
        if (fp == NULL) {
            (void)close(fd);
            return -1;
        }
        if (fputs("{\"model\":\"deepseek-chat\",\"messages\":[", fp) < 0) {
            (void)fclose(fp);
            return -1;
        }
        if (fputs("{\"role\":\"system\",\"content\":\"", fp) < 0) {
            (void)fclose(fp);
            return -1;
        }
        pos = 0U;
        if (json_append_escaped(sys, body, sizeof body, &pos) != 0) {
            (void)fclose(fp);
            return -1;
        }
        if (fputs(body, fp) < 0) {
            (void)fclose(fp);
            return -1;
        }
        if (fputs("\"},{\"role\":\"user\",\"content\":\"", fp) < 0) {
            (void)fclose(fp);
            return -1;
        }
        pos = 0U;
        body[0] = '\0';
        if (json_append_escaped(intent, body, sizeof body, &pos) != 0) {
            (void)fclose(fp);
            return -1;
        }
        if (fputs(body, fp) < 0) {
            (void)fclose(fp);
            return -1;
        }
        if (fputs("\"}],\"temperature\":0.2}", fp) < 0) {
            (void)fclose(fp);
            return -1;
        }
        if (fclose(fp) != 0) {
            return -1;
        }
    }
    return 0;
}

static int read_response_file(const char *path, char *buf, size_t bufsz) {
    FILE *fp;
    size_t n;

    fp = fopen(path, "rb");
    if (fp == NULL) {
        return -1;
    }
    n = fread(buf, 1U, bufsz - 1U, fp);
    (void)fclose(fp);
    buf[n] = '\0';
    return (int)n;
}

static const char *skip_ws(const char *p) {
    while (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r') {
        p++;
    }
    return p;
}

/* Parse JSON string starting at opening quote; writes unescaped into out (<= outsz-1). */
static int parse_json_string(const char *start, char *out, size_t outsz) {
    const char *p;
    size_t o;

    if (start == NULL || *start != '"' || out == NULL || outsz == 0U) {
        return -1;
    }
    p = start + 1;
    o = 0U;
    while (*p != '\0' && *p != '"') {
        if (*p == '\\' && p[1] != '\0') {
            p++;
            if (*p == 'n') {
                if (o + 1U >= outsz) {
                    return -1;
                }
                out[o++] = '\n';
            } else if (*p == 't') {
                if (o + 1U >= outsz) {
                    return -1;
                }
                out[o++] = '\t';
            } else if (*p == 'r') {
                if (o + 1U >= outsz) {
                    return -1;
                }
                out[o++] = '\r';
            } else {
                if (o + 1U >= outsz) {
                    return -1;
                }
                out[o++] = *p;
            }
            p++;
        } else {
            if (o + 1U >= outsz) {
                return -1;
            }
            out[o++] = *p++;
        }
    }
    if (*p != '"') {
        return -1;
    }
    out[o] = '\0';
    return (int)(p - start + 1);
}

/* Find "primitive" : "VALUE" in json object */
static int extract_primitive(const char *json, char *out, size_t outsz) {
    const char *p;
    int consumed;

    p = strstr(json, "\"primitive\"");
    if (p == NULL) {
        return -1;
    }
    p = strchr(p, ':');
    if (p == NULL) {
        return -1;
    }
    p = skip_ws(p + 1);
    consumed = parse_json_string(p, out, outsz);
    if (consumed < 0) {
        return -1;
    }
    return 0;
}

/* After opening { of params object, read pairs until closing } */
static int parse_params_object(const char *open_brace, AmsResult *r) {
    const char *p;
    char kbuf[64];
    char vbuf[256];
    int ck;
    int cv;

    p = skip_ws(open_brace + 1);
    if (*p == '}') {
        return 0;
    }
    while (*p != '\0' && *p != '}') {
        if (*p != '"') {
            return -1;
        }
        ck = parse_json_string(p, kbuf, sizeof kbuf);
        if (ck < 0) {
            return -1;
        }
        p = skip_ws(p + (size_t)ck);
        if (*p != ':') {
            return -1;
        }
        p = skip_ws(p + 1);
        if (*p != '"') {
            return -1;
        }
        cv = parse_json_string(p, vbuf, sizeof vbuf);
        if (cv < 0) {
            return -1;
        }
        p = skip_ws(p + (size_t)cv);
        if (r->param_count >= AMS_PARAM_MAX) {
            return -1;
        }
        (void)snprintf(r->param_keys[r->param_count], sizeof r->param_keys[0], "%s", kbuf);
        (void)snprintf(r->params[r->param_count], sizeof r->params[0], "%s", vbuf);
        r->param_count++;
        if (*p == ',') {
            p = skip_ws(p + 1);
        } else if (*p == '}') {
            break;
        } else if (*p == '\0') {
            break;
        } else {
            return -1;
        }
    }
    return 0;
}

static int extract_params(const char *json, AmsResult *r) {
    const char *p;
    const char *brace;

    p = strstr(json, "\"params\"");
    if (p == NULL) {
        r->param_count = 0;
        return 0;
    }
    p = strchr(p, ':');
    if (p == NULL) {
        return -1;
    }
    p = skip_ws(p + 1);
    if (*p != '{') {
        return -1;
    }
    brace = p;
    return parse_params_object(brace, r);
}

/* Extract assistant text from DeepSeek/OpenAI JSON; may contain escaped inner JSON */
static int extract_content_string(const char *http_body, char *out, size_t outsz) {
    const char *p;
    const char *q;
    int consumed;
    const char *from;

    from = strstr(http_body, "\"assistant\"");
    p = NULL;
    if (from != NULL) {
        p = strstr(from, "\"content\"");
    }
    if (p == NULL) {
        p = strstr(http_body, "\"content\"");
    }
    if (p == NULL) {
        return -1;
    }
    p = strchr(p, ':');
    if (p == NULL) {
        return -1;
    }
    p = skip_ws(p + 1);
    /* Sometimes content is string with escapes */
    if (*p != '"') {
        return -1;
    }
    consumed = parse_json_string(p, out, outsz);
    if (consumed < 0) {
        return -1;
    }
    /* Trim surrounding whitespace in inner JSON */
    q = out;
    while (*q == ' ' || *q == '\t' || *q == '\n') {
        q++;
    }
    if (q != out) {
        (void)memmove(out, q, strlen(q) + 1U);
    }
    return 0;
}

/* If model returned JSON without wrapping in content escapes, try raw body */
static const char *find_inner_json_start(const char *s) {
    const char *p;

    p = strchr(s, '{');
    return p;
}

void icm_ams_decompose(const char *intent, const char *api_key, AmsResult *result) {
    char req_path[64];
    char resp_path[64];
    char cmd[CURL_CMD_MAX];
    IcmResult sh;
    static char http_body[RESP_READ_MAX];
    static char inner[8192];
    int nr;
    const char *inner_json;

    ams_clear(result);
    if (intent == NULL || api_key == NULL || result == NULL || api_key[0] == '\0') {
        result->status = ICM_ERR;
        (void)snprintf(result->error, sizeof result->error, "invalid argument or empty API key");
        return;
    }

    (void)snprintf(resp_path, sizeof resp_path, "/tmp/icm_ams_respXXXXXX");
    {
        int fd = mkstemp(resp_path);
        if (fd < 0) {
            result->status = ICM_ERR;
            (void)snprintf(result->error, sizeof result->error, "mkstemp resp failed");
            return;
        }
        (void)close(fd);
    }

    if (write_request_file(intent, req_path, sizeof req_path) != 0) {
        result->status = ICM_ERR;
        (void)snprintf(result->error, sizeof result->error, "request file failed");
        (void)unlink(resp_path);
        return;
    }

    /* shell-safe: strip single quotes from key for command line */
    {
        char key_safe[512];
        size_t i;
        size_t j;
        for (i = 0U, j = 0U; api_key[i] != '\0' && j + 1U < sizeof key_safe; i++) {
            if (api_key[i] == '\'') {
                continue;
            }
            key_safe[j++] = api_key[i];
        }
        key_safe[j] = '\0';
        (void)snprintf(cmd, sizeof cmd,
                       "curl -sS -f -m 90 -o '%s' -X POST 'https://api.deepseek.com/chat/completions' "
                       "-H 'Content-Type: application/json' "
                       "-H 'Authorization: Bearer %s' "
                       "-d @'%s'",
                       resp_path, key_safe, req_path);
    }

    icm_shell_exec(cmd, 120, &sh);
    if (sh.status != 0) {
        result->status = ICM_ERR;
        (void)snprintf(result->error, sizeof result->error, "curl exit %d", sh.status);
        if (sh.size > 0U) {
            (void)snprintf(result->error, sizeof result->error, "curl: %.200s", sh.data);
        }
        (void)unlink(req_path);
        (void)unlink(resp_path);
        return;
    }

    nr = read_response_file(resp_path, http_body, sizeof http_body);
    (void)unlink(req_path);
    (void)unlink(resp_path);
    if (nr < 0) {
        result->status = ICM_ERR;
        (void)snprintf(result->error, sizeof result->error, "read response failed");
        return;
    }

    inner[0] = '\0';
    if (extract_content_string(http_body, inner, sizeof inner) == 0) {
        inner_json = skip_ws(inner);
    } else {
        inner_json = find_inner_json_start(http_body);
        if (inner_json == NULL) {
            result->status = ICM_ERR;
            (void)snprintf(result->error, sizeof result->error, "no JSON in response");
            return;
        }
    }

    if (extract_primitive(inner_json, result->primitive_id, sizeof result->primitive_id) != 0) {
        /* try full http body */
        if (extract_primitive(http_body, result->primitive_id, sizeof result->primitive_id) != 0) {
            result->status = ICM_ERR;
            (void)snprintf(result->error, sizeof result->error, "parse primitive failed");
            return;
        }
        if (extract_params(http_body, result) != 0) {
            result->status = ICM_ERR;
            (void)snprintf(result->error, sizeof result->error, "parse params failed");
            return;
        }
    } else {
        if (extract_params(inner_json, result) != 0) {
            result->status = ICM_ERR;
            (void)snprintf(result->error, sizeof result->error, "parse params failed");
            return;
        }
    }

    /* normalize primitive id trim */
    {
        char *t = result->primitive_id;
        while (*t != '\0' && isspace((unsigned char)*t)) {
            t++;
        }
        if (t != result->primitive_id) {
            (void)memmove(result->primitive_id, t, strlen(t) + 1U);
        }
    }

    result->status = ICM_OK;
}
