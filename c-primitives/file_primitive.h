#ifndef ICM_FILE_PRIMITIVE_H
#define ICM_FILE_PRIMITIVE_H

#include <stddef.h>

#define ICM_OK   0
#define ICM_ERR -1

typedef struct {
    int status;
    char data[4096];
    size_t size;
    char error[256];
} IcmResult;

/**
 * Read file contents into result->data (up to sizeof(data)-1 bytes).
 * Sets result->size to bytes read; null-terminates data when there is room.
 * On failure: result->status = ICM_ERR, message in result->error.
 */
void icm_file_read(const char *path, IcmResult *result);

/**
 * Write or append content to path. mode: "w" (truncate) or "a" (append).
 * Returns ICM_OK on success, ICM_ERR on failure (logs [PRIMITIVE] message).
 */
int icm_file_write(const char *path, const char *content, const char *mode);

/**
 * List directory entries into result->data, one name per line.
 * On failure: result->status = ICM_ERR, message in result->error.
 */
void icm_file_list(const char *dir_path, IcmResult *result);

#endif /* ICM_FILE_PRIMITIVE_H */
