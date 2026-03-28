#ifndef ICM_HTTP_GET_H
#define ICM_HTTP_GET_H

#include "file_primitive.h"

#include <stddef.h>

/**
 * HTTP GET result. `status` is ICM_OK / ICM_ERR (primitive outcome).
 * `status_code` is the numeric HTTP status from the response line (e.g. 200), or 0 if unknown.
 */
typedef struct {
    int status_code;
    char body[8192];
    size_t body_size;
    char headers[2048];
    char error[256];
    int status;
} HttpResult;

/**
 * Perform HTTP/1.1 GET on `url` (http:// only). Uses raw sockets (no libcurl).
 * `timeout_sec` > 0 sets SO_RCVTIMEO / SO_SNDTIMEO on the socket; <= 0 leaves defaults.
 */
void icm_http_get(const char *url, int timeout_sec, HttpResult *result);

#endif /* ICM_HTTP_GET_H */
