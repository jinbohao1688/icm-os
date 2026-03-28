CC = gcc
CFLAGS = -std=c99 -Wall -Wextra -pedantic

# Avoid naming the phony target the same as the binary (circular dependency).
EXEC = test

.PHONY: test clean

test:
	$(CC) $(CFLAGS) -o $(EXEC) file_primitive.c file_primitive_test.c
	./$(EXEC)

clean:
	rm -f $(EXEC)
