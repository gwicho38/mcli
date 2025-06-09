#! /usr/bin/env bash


oi(
./open-interpreter/open_interpreter.py
)

# Call the appropriate function if it's provided as an argument
if [ -n "$1" ]; then
  "$@"
fi
