/* For kill(2), usleep(3) with glibc in -std=c99. */
#ifndef _POSIX_C_SOURCE
#define _POSIX_C_SOURCE 200809L
#endif

#include "shell_exec.h"

#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

static void sleep_ms(int ms) {
    struct timespec ts;
    ts.tv_sec = (time_t)(ms / 1000);
    ts.tv_nsec = (long)((ms % 1000) * 1000000);
    (void)nanosleep(&ts, NULL);
}

#define READ_CHUNK 4096

static void result_clear(IcmResult *result) {
    if (result == NULL) {
        return;
    }
    result->status = ICM_OK;
    result->data[0] = '\0';
    result->size = 0;
    result->error[0] = '\0';
}

static int append_data(IcmResult *result, const char *buf, size_t n) {
    size_t cap;
    size_t room;
    size_t take;

    if (result == NULL || n == 0U) {
        return 0;
    }
    cap = sizeof result->data;
    if (result->size >= cap) {
        return -1;
    }
    room = cap - 1U - result->size;
    take = n < room ? n : room;
    (void)memcpy(result->data + result->size, buf, take);
    result->size += take;
    result->data[result->size] = '\0';
    return (take < n) ? -1 : 0;
}

static void drain_pipe(int fd, IcmResult *result) {
    char buf[READ_CHUNK];
    ssize_t n;

    for (;;) {
        n = read(fd, buf, sizeof buf);
        if (n > 0) {
            (void)append_data(result, buf, (size_t)n);
        } else if (n == 0) {
            break;
        } else {
            if (errno == EAGAIN || errno == EWOULDBLOCK) {
                break;
            }
            break;
        }
    }
}

static void set_wait_status(IcmResult *result, int wstatus) {
    if (WIFEXITED(wstatus)) {
        result->status = WEXITSTATUS(wstatus);
    } else if (WIFSIGNALED(wstatus)) {
        result->status = 128 + WTERMSIG(wstatus);
    } else {
        result->status = ICM_ERR;
        (void)snprintf(result->error, sizeof result->error, "abnormal child status");
    }
}

void icm_shell_exec(const char *command, int timeout_sec, IcmResult *result) {
    int pipefd[2];
    pid_t pid;
    time_t start;
    int wstatus = 0;
    int timed_out = 0;

    result_clear(result);
    if (command == NULL || result == NULL) {
        if (result != NULL) {
            result->status = ICM_ERR;
            (void)snprintf(result->error, sizeof result->error, "invalid argument");
        }
        printf("[SHELL_EXEC] invalid argument\n");
        return;
    }

    if (pipe(pipefd) != 0) {
        result->status = ICM_ERR;
        (void)snprintf(result->error, sizeof result->error, "pipe: %s", strerror(errno));
        printf("[SHELL_EXEC] pipe failed: %s\n", result->error);
        return;
    }

    if (fcntl(pipefd[0], F_SETFL, O_NONBLOCK) != 0) {
        result->status = ICM_ERR;
        (void)snprintf(result->error, sizeof result->error, "fcntl: %s", strerror(errno));
        printf("[SHELL_EXEC] fcntl failed: %s\n", result->error);
        (void)close(pipefd[0]);
        (void)close(pipefd[1]);
        return;
    }

    pid = fork();
    if (pid < 0) {
        result->status = ICM_ERR;
        (void)snprintf(result->error, sizeof result->error, "fork: %s", strerror(errno));
        printf("[SHELL_EXEC] fork failed: %s\n", result->error);
        (void)close(pipefd[0]);
        (void)close(pipefd[1]);
        return;
    }

    if (pid == 0) {
        char *argv_sh[] = {"sh", "-c", (char *)command, NULL};

        (void)close(pipefd[0]);
        if (dup2(pipefd[1], STDOUT_FILENO) < 0) {
            _exit(126);
        }
        if (dup2(pipefd[1], STDERR_FILENO) < 0) {
            _exit(126);
        }
        if (pipefd[1] != STDOUT_FILENO && pipefd[1] != STDERR_FILENO) {
            (void)close(pipefd[1]);
        }
        (void)signal(SIGPIPE, SIG_DFL);
        execvp("/bin/sh", argv_sh);
        _exit(127);
    }

    (void)close(pipefd[1]);
    start = time(NULL);

    for (;;) {
        pid_t w;

        drain_pipe(pipefd[0], result);

        w = waitpid(pid, &wstatus, WNOHANG);
        if (w == pid) {
            drain_pipe(pipefd[0], result);
            break;
        }
        if (w < 0) {
            result->status = ICM_ERR;
            (void)snprintf(result->error, sizeof result->error, "waitpid: %s", strerror(errno));
            printf("[SHELL_EXEC] waitpid error: %s\n", result->error);
            (void)close(pipefd[0]);
            return;
        }

        if (timeout_sec > 0 && (time(NULL) - start) >= (time_t)timeout_sec) {
            timed_out = 1;
            (void)kill(pid, SIGKILL);
            printf("[SHELL_EXEC] timeout after %d s, sent SIGKILL to pid %ld\n",
                   timeout_sec, (long)pid);
            for (;;) {
                w = waitpid(pid, &wstatus, 0);
                if (w == pid) {
                    break;
                }
                if (w < 0 && errno == EINTR) {
                    continue;
                }
                result->status = ICM_ERR;
                (void)snprintf(result->error, sizeof result->error, "waitpid: %s", strerror(errno));
                printf("[SHELL_EXEC] waitpid after kill: %s\n", result->error);
                (void)close(pipefd[0]);
                return;
            }
            drain_pipe(pipefd[0], result);
            break;
        }

        sleep_ms(10);
    }

    (void)close(pipefd[0]);

    if (timed_out) {
        (void)snprintf(result->error, sizeof result->error, "command timed out");
        set_wait_status(result, wstatus);
        printf("[SHELL_EXEC] done (timeout) exit_status=%d data_bytes=%zu\n",
               result->status, result->size);
        return;
    }

    set_wait_status(result, wstatus);
    printf("[SHELL_EXEC] done cmd=%.60s%s exit_status=%d data_bytes=%zu\n",
           command, strlen(command) > 60U ? "..." : "", result->status, result->size);
}
