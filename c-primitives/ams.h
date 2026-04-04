#ifndef ICM_AMS_H
#define ICM_AMS_H

#include "file_primitive.h"

#define AMS_PARAM_MAX 8

typedef struct {
    char primitive_id[64];
    char params[AMS_PARAM_MAX][256];
    char param_keys[AMS_PARAM_MAX][64];
    int param_count;
    char error[256];
    int status;
} AmsResult;

/**
 * Decompose natural-language `intent` via DeepSeek (HTTPS through curl + shell_exec).
 * `api_key` must be non-NULL and non-empty.
 * On success: status == ICM_OK, primitive_id and params filled.
 */
void icm_ams_decompose(const char *intent, const char *api_key, AmsResult *result);

#endif /* ICM_AMS_H */
