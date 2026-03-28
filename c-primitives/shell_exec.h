#ifndef ICM_SHELL_EXEC_H
#define ICM_SHELL_EXEC_H

#include "file_primitive.h"

/**
 * Run `command` via /bin/sh -c (fork + execvp, no system()).
 * Merges child stdout and stderr into result->data (truncated to buffer).
 * On normal exit: result->status is the shell's wait-style exit status
 *   (0–255 if WIFEXITED; if killed by signal, 128 + WTERMSIG).
 * On spawn/pipe failure: result->status == ICM_ERR, message in result->error.
 * timeout_sec > 0: SIGKILL child after that many seconds; sets result->error.
 * timeout_sec <= 0: wait until the child exits (no time limit).
 */
void icm_shell_exec(const char *command, int timeout_sec, IcmResult *result);

#endif /* ICM_SHELL_EXEC_H */
