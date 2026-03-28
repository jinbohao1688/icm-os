CC = gcc
CFLAGS = -std=c99 -Wall -Wextra -pedantic

# Do not name binaries "test" while using a phony target `test`.
EXEC_FILE = icm_c_file_test
EXEC_SHELL = icm_c_shell_test

.PHONY: test test-file test-shell clean all

all: $(EXEC_FILE) $(EXEC_SHELL)

$(EXEC_FILE): file_primitive.c file_primitive_test.c file_primitive.h
	$(CC) $(CFLAGS) -o $(EXEC_FILE) file_primitive.c file_primitive_test.c

$(EXEC_SHELL): shell_exec.c shell_exec_test.c shell_exec.h file_primitive.h
	$(CC) $(CFLAGS) -o $(EXEC_SHELL) shell_exec.c shell_exec_test.c

test-file: $(EXEC_FILE)
	./$(EXEC_FILE)

test-shell: $(EXEC_SHELL)
	./$(EXEC_SHELL)

test: $(EXEC_FILE) $(EXEC_SHELL)
	./$(EXEC_FILE)
	./$(EXEC_SHELL)

clean:
	rm -f $(EXEC_FILE) $(EXEC_SHELL)
