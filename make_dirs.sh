#!/bin/bash
# make_dirs.sh
# Create directories for Russian audio flashcards

# Always run from project root
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd "$PROJECT_DIR"

# Create directories if they don’t exist
mkdir -p audio_native
mkdir -p audio_user

echo "✅ Directories created (or already exist):"
echo "   $PROJECT_DIR/audio_native"
echo "   $PROJECT_DIR/audio_user"
