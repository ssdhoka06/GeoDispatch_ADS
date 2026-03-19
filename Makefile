# GeoDispatch ADS — Makefile
#
# Targets:
#   make              → build everything (shared lib + bench + tests)
#   make run-test     → build and run unit tests
#   make run-bench    → build and run benchmark
#   make clean        → remove all build outputs
#
# The shared library (geodispatch.so / .dll) is placed in python/
# so that geodispatch.py can find it via ctypes at import time.

CC     = gcc
CFLAGS = -std=c11 -O2 -Wall -Wextra -fPIC

# ── detect OS for shared library extension ────────────────────────────────────
UNAME_S := $(shell uname -s 2>/dev/null)
ifneq ($(findstring MINGW,$(UNAME_S)),)
    SO_EXT   = dll
    SO_FLAGS = -shared
else ifneq ($(findstring MSYS,$(UNAME_S)),)
    SO_EXT   = dll
    SO_FLAGS = -shared
else ifeq ($(UNAME_S),Darwin)
    SO_EXT   = dylib
    SO_FLAGS = -dynamiclib
else
    SO_EXT   = so
    SO_FLAGS = -shared
endif

# ── sources ───────────────────────────────────────────────────────────────────
LIB_SRC = src/kd.c src/kd_dynamic.c

# ── output paths ──────────────────────────────────────────────────────────────
SO      = python/geodispatch.$(SO_EXT)
BENCH   = bench
TEST    = test_kd

# ── default target ────────────────────────────────────────────────────────────
.PHONY: all clean run-bench run-test
all: $(SO) $(BENCH) $(TEST)

# Shared library — loaded by python/geodispatch.py via ctypes
$(SO): $(LIB_SRC)
	$(CC) $(CFLAGS) $(SO_FLAGS) -o $@ $^ -lm

# Benchmarking executable
$(BENCH): src/bench.c $(LIB_SRC)
	$(CC) $(CFLAGS) -o $@ $^ -lm

# Unit test executable
$(TEST): src/test.c $(LIB_SRC)
	$(CC) $(CFLAGS) -o $@ $^ -lm

run-bench: $(BENCH)
	./$(BENCH)

run-test: $(TEST)
	./$(TEST)

clean:
	rm -f $(SO) $(BENCH) $(TEST)
