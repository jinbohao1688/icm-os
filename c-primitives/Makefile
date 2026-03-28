CC = gcc
# getaddrinfo / POSIX networking
CFLAGS = -std=c99 -Wall -Wextra -pedantic -D_POSIX_C_SOURCE=200809L

# Do not name binaries "test" while using a phony target `test`.
EXEC_FILE = icm_c_file_test
EXEC_SHELL = icm_c_shell_test
EXEC_DNS = icm_c_dns_test
EXEC_HTTP = icm_c_http_test
ICM_SHELL = icm_shell
# Static link for initramfs (no shared libc in minimal root); QEMU/ISO 可直接运行
ICM_SHELL_LDFLAGS = -static

.PHONY: test test-file test-shell test-dns test-http clean all run

all: $(EXEC_FILE) $(EXEC_SHELL) $(EXEC_DNS) $(EXEC_HTTP) $(ICM_SHELL)

$(EXEC_FILE): file_primitive.c file_primitive_test.c file_primitive.h
	$(CC) $(CFLAGS) -o $(EXEC_FILE) file_primitive.c file_primitive_test.c

$(EXEC_SHELL): shell_exec.c shell_exec_test.c shell_exec.h file_primitive.h
	$(CC) $(CFLAGS) -o $(EXEC_SHELL) shell_exec.c shell_exec_test.c

$(EXEC_DNS): dns_resolve.c dns_resolve_test.c dns_resolve.h file_primitive.h
	$(CC) $(CFLAGS) -o $(EXEC_DNS) dns_resolve.c dns_resolve_test.c

$(EXEC_HTTP): http_get.c http_get_test.c http_get.h file_primitive.h
	$(CC) $(CFLAGS) -o $(EXEC_HTTP) http_get.c http_get_test.c

$(ICM_SHELL): icm_shell.c file_primitive.c shell_exec.c dns_resolve.c http_get.c \
		file_primitive.h shell_exec.h dns_resolve.h http_get.h
	$(CC) $(CFLAGS) $(ICM_SHELL_LDFLAGS) -o $(ICM_SHELL) icm_shell.c file_primitive.c shell_exec.c \
		dns_resolve.c http_get.c

run: $(ICM_SHELL)
	./$(ICM_SHELL)

test-file: $(EXEC_FILE)
	./$(EXEC_FILE)

test-shell: $(EXEC_SHELL)
	./$(EXEC_SHELL)

test-dns: $(EXEC_DNS)
	./$(EXEC_DNS)

test-http: $(EXEC_HTTP)
	./$(EXEC_HTTP)

test: $(EXEC_FILE) $(EXEC_SHELL) $(EXEC_DNS) $(EXEC_HTTP)
	./$(EXEC_FILE)
	./$(EXEC_SHELL)
	./$(EXEC_DNS)
	./$(EXEC_HTTP)

clean:
	rm -f $(EXEC_FILE) $(EXEC_SHELL) $(EXEC_DNS) $(EXEC_HTTP) $(ICM_SHELL)
