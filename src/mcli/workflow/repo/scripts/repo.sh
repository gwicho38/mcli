#! /usr/bin/env bash

# Call the appropriate function if it's provided as an argument
#
if [ -n "$1" ]; then
  "$@"
fi
