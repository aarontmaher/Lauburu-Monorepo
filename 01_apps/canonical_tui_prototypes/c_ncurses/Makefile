CC ?= gcc
CFLAGS ?= -O2 -Wall -Wextra -std=c99
LDFLAGS ?= -lncurses

SRC = canonical_tui.c
TARGET = bin/canonical_tui_c

all: $(TARGET)

$(TARGET): $(SRC)
	@mkdir -p bin
	$(CC) $(CFLAGS) $(SRC) -o $(TARGET) $(LDFLAGS)

verify: $(TARGET)
	./$(TARGET) --verify

clean:
	rm -rf bin

.PHONY: all verify clean
