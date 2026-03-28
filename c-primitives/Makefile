CC = gcc
# getaddrinfo / POSIX networking
CFLAGS = -std=c99 -Wall -Wextra -pedantic -D_POSIX_C_SOURCE=200809L

# Do not name binaries "test" while using a phony target `test`.
EXEC_FILE = icm_c_file_test
EXEC_SHELL = icm_c_shell_test
EXEC_DNS = icm_c_dns_test

.PHONY: test test-file test-shell test-dns clean all

all: $(EXEC_FILE) $(EXEC_SHELL) $(EXEC_DNS)

$(EXEC_FILE): file_primitive.c file_primitive_test.c file_primitive.h
	$(CC) $(CFLAGS) -o $(EXEC_FILE) file_primitive.c file_primitive_test.c

$(EXEC_SHELL): shell_exec.c shell_exec_test.c shell_exec.h file_primitive.h
	$(CC) $(CFLAGS) -o $(EXEC_SHELL) shell_exec.c shell_exec_test.c

$(EXEC_DNS): dns_resolve.c dns_resolve_test.c dns_resolve.h file_primitive.h
	$(CC) $(CFLAGS) -o $(EXEC_DNS) dns_resolve.c dns_resolve_test.c

test-file: $(EXEC_FILE)
	./$(EXEC_FILE)

test-shell: $(EXEC_SHELL)
	./$(EXEC_SHELL)

test-dns: $(EXEC_DNS)
	./$(EXEC_DNS)

test: $(EXEC_FILE) $(EXEC_SHELL) $(EXEC_DNS)
	./$(EXEC_FILE)
	./$(EXEC_SHELL)
	./$(EXEC_DNS)

clean:
	rm -f $(EXEC_FILE) $(EXEC_SHELL) $(EXEC_DNS)
