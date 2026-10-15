CC ?= clang
CFLAGS ?= -O3 -Wall -Wextra -std=c11
LDFLAGS ?= -lm

TARGET = lauburu_keychain_sniffer
SRC = lauburu_keychain_sniffer.c

all: $(TARGET)

$(TARGET): $(SRC)
	$(CC) $(CFLAGS) -o $(TARGET) $(SRC) $(LDFLAGS)

test: $(TARGET)
	./$(TARGET) --test
	./$(TARGET) --test --json

clean:
	rm -f $(TARGET)
