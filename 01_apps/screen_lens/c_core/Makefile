# 01_apps/screen_lens/c_core/Makefile
# Standard C11 build automation for Lauburu Sovereign Storage Pooling

CC ?= clang
CFLAGS ?= -std=c11 -O3 -Wall -Wextra -fPIC

.PHONY: all clean test

all: liblauburu_storage.dylib lauburu_storage_bench

liblauburu_storage.dylib: lauburu_pooled_storage.c lauburu_pooled_storage.h
	$(CC) $(CFLAGS) -shared -o $@ lauburu_pooled_storage.c

lauburu_storage_bench: test_pooled_storage.c lauburu_pooled_storage.c lauburu_pooled_storage.h
	$(CC) $(CFLAGS) -o $@ test_pooled_storage.c lauburu_pooled_storage.c

test: lauburu_storage_bench
	./lauburu_storage_bench

clean:
	rm -f liblauburu_storage.dylib lauburu_storage_bench
