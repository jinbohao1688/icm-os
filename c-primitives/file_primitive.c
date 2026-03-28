#include "file_primitive.h"

#include <dirent.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>

static void result_init(IcmResult *result) {
    if (result == NULL) {
        return;
    }
    result->status = ICM_OK;
    result->data[0] = '\0';
    result->size = 0;
    result->error[0] = '\0';
}

void icm_file_read(const char *path, IcmResult *result) {
    FILE *fp;
    size_t nread;
    const size_t max_read = sizeof result->data - 1U;

    result_init(result);
    if (path == NULL || result == NULL) {
        if (result != NULL) {
            result->status = ICM_ERR;
            (void)snprintf(result->error, sizeof result->error, "invalid argument");
        }
        printf("[PRIMITIVE] icm_file_read: invalid argument\n");
        return;
    }

    fp = fopen(path, "rb");
    if (fp == NULL) {
        result->status = ICM_ERR;
        (void)snprintf(result->error, sizeof result->error, "fopen: %s", strerror(errno));
        printf("[PRIMITIVE] icm_file_read: %s (%s)\n", result->error, path);
        return;
    }

    nread = fread(result->data, 1U, max_read, fp);
    if (ferror(fp)) {
        result->status = ICM_ERR;
        (void)snprintf(result->error, sizeof result->error, "fread: %s", strerror(errno));
        printf("[PRIMITIVE] icm_file_read: %s (%s)\n", result->error, path);
        (void)fclose(fp);
        return;
    }

    result->data[nread] = '\0';

    /* If buffer full, ensure no further readable bytes */
    if (nread == max_read) {
        int extra = fgetc(fp);
        if (extra != EOF) {
            result->status = ICM_ERR;
            result->data[0] = '\0';
            result->size = 0;
            (void)snprintf(result->error, sizeof result->error, "file larger than buffer (%zu bytes)",
                           max_read);
            printf("[PRIMITIVE] icm_file_read: %s (%s)\n", result->error, path);
            (void)fclose(fp);
            return;
        }
    }

    result->size = nread;
    (void)fclose(fp);
    printf("[PRIMITIVE] icm_file_read: ok path=%s bytes=%zu\n", path, result->size);
}

int icm_file_write(const char *path, const char *content, const char *mode) {
    FILE *fp;
    const char *open_mode;
    size_t len;
    size_t written;

    if (path == NULL || content == NULL || mode == NULL) {
        printf("[PRIMITIVE] icm_file_write: invalid argument\n");
        return ICM_ERR;
    }

    if (strcmp(mode, "w") == 0) {
        open_mode = "w";
    } else if (strcmp(mode, "a") == 0) {
        open_mode = "a";
    } else {
        printf("[PRIMITIVE] icm_file_write: invalid mode \"%s\" (use w or a)\n", mode);
        return ICM_ERR;
    }

    fp = fopen(path, open_mode);
    if (fp == NULL) {
        printf("[PRIMITIVE] icm_file_write: fopen failed %s: %s\n", path, strerror(errno));
        return ICM_ERR;
    }

    len = strlen(content);
    written = fwrite(content, 1U, len, fp);
    if (written != len || ferror(fp)) {
        printf("[PRIMITIVE] icm_file_write: fwrite failed %s: %s\n", path, strerror(errno));
        (void)fclose(fp);
        return ICM_ERR;
    }

    if (fclose(fp) != 0) {
        printf("[PRIMITIVE] icm_file_write: fclose failed %s: %s\n", path, strerror(errno));
        return ICM_ERR;
    }

    printf("[PRIMITIVE] icm_file_write: ok path=%s mode=%s bytes=%zu\n", path, mode, written);
    return ICM_OK;
}

void icm_file_list(const char *dir_path, IcmResult *result) {
    DIR *dir;
    struct dirent *ent;
    size_t pos = 0;
    const size_t cap = sizeof result->data;

    result_init(result);
    if (dir_path == NULL || result == NULL) {
        if (result != NULL) {
            result->status = ICM_ERR;
            (void)snprintf(result->error, sizeof result->error, "invalid argument");
        }
        printf("[PRIMITIVE] icm_file_list: invalid argument\n");
        return;
    }

    dir = opendir(dir_path);
    if (dir == NULL) {
        result->status = ICM_ERR;
        (void)snprintf(result->error, sizeof result->error, "opendir: %s", strerror(errno));
        printf("[PRIMITIVE] icm_file_list: %s (%s)\n", result->error, dir_path);
        return;
    }

    while ((ent = readdir(dir)) != NULL) {
        size_t n = strlen(ent->d_name);
        /* need space for name + '\n' + optional final '\0' */
        if (pos + n + 2U > cap) {
            result->status = ICM_ERR;
            (void)snprintf(result->error, sizeof result->error, "listing truncated (buffer full)");
            printf("[PRIMITIVE] icm_file_list: %s (%s)\n", result->error, dir_path);
            (void)closedir(dir);
            return;
        }
        (void)memcpy(result->data + pos, ent->d_name, n);
        pos += n;
        result->data[pos++] = '\n';
    }

    if (closedir(dir) != 0) {
        result->status = ICM_ERR;
        (void)snprintf(result->error, sizeof result->error, "closedir: %s", strerror(errno));
        printf("[PRIMITIVE] icm_file_list: %s (%s)\n", result->error, dir_path);
        return;
    }

    if (pos < cap) {
        result->data[pos] = '\0';
    }
    result->size = pos;
    printf("[PRIMITIVE] icm_file_list: ok dir=%s bytes=%zu\n", dir_path, result->size);
}
