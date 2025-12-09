#!/usr/bin/env bash
set -e

# ========= CONFIG =========
CC=gcc
CFLAGS="-O2 -Wall -Wextra -std=c11"
INCLUDES="-Ilibs"

# Fuente principal
MAIN_SRC="rf_metrics.c"

# Todos los .c dentro de libs/
LIB_SRCS=$(ls libs/*.c)

# Ejecutable final
OUT="rf_metrics"

# Librerías a enlazar
LIBS="-lhackrf -lzmq -lcjson -lfftw3 -lm -lpthread -lliquid"

echo "Compilando motor C..."
echo "  Fuentes: $MAIN_SRC $LIB_SRCS"
echo "  Output : $OUT"

$CC $CFLAGS $INCLUDES $MAIN_SRC $LIB_SRCS -o $OUT $LIBS

echo "✅ Build completo. Ejecutable: ./$OUT"

