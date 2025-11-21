#!/bin/bash
set -e

# Build script for Nuitka
echo "Building Serena Native Wrapper with Nuitka..."

# Check if Nuitka is installed
if ! command -v python -m nuitka &> /dev/null; then
    echo "Nuitka not found. Installing..."
    pip install nuitka
fi

# Output directory
OUTPUT_DIR="dist"
mkdir -p $OUTPUT_DIR

# Build
python -m nuitka src/serena_native/cli.py \
    --standalone \
    --onefile \
    --include-package=serena_native \
    --output-filename=serena-native \
    --output-dir=$OUTPUT_DIR

echo "Build complete. Binary is at $OUTPUT_DIR/serena-native"
