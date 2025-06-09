#! /usr/bin/env bash

# export AUTH='-u BA:BA'
# export MCLI_ENDPOINT='https://755d66jp-8080.usw3.devtunnels.ms/'
# export MCLI_TENANT='mcli
# export MCLI_TAG='mcli'
# export SUBDIR='c17_flight_recorder_data'

# # First argument to this script is the file to upload.
# export FILE="$1"

# # Make sure file was passed in.
# if [ -z "$FILE" ]; then
#   echo "ERROR: No file specified."
#   echo ""
#   echo "Usage: $0 <file>"
#   exit 1
# fi

# # Make sure file exists.
# if [ ! -f "$FILE" ]; then
#   echo "ERROR: File does not exist: $FILE"
#   echo ""
#   echo "Usage: $0 <file>"
#   exit 1
# fi

# FILE_NAME=$(basename "$FILE")
# MIME_TYPE=$(file --mime-type -b "$FILE")

# echo "$FILE_NAME $MIME_TYPE"

# curl \
#   -v \
#   -H "authorization: $AUTH" \
#   -H "Content-Type: $MIME_TYPE" \
#   -X PUT \
#   -T "$FILE" \
#   "$MCLI_ENDPOINT/file/1/$MCLI_TENANT/$MCLI_TAG/$SUBDIR/$FILE_NAME"
 
request () {
  echo "$@"
  exit 0
    # Use awk to match and extract sections between MCLI_ and _MCLI
    # Use awk to match and extract sections between MCLI_ and _MCLI
  echo "$input" | awk '{
      while(match($0, /MCLI_(.*?)/)) {
          print substr($0, RSTART+0, RLENGTH-0);  # Extract and print each section
          $0 = substr($0, RSTART);  # Reduce the string for the next match
      }
  }' | while read -r line; do
      array+=("$line")  # Append each extracted section to the array
  done
  echo "$input" | awk '{
      while(match($0, /(.*?)_MCLI/)) {
          print substr($0, RSTART+0, RLENGTH-0);  # Extract and print each section
          $0 = substr($0, RSTART);  # Reduce the string for the next match
      }
  }' | while read -r line; do
      array+=("$line")  # Append each extracted section to the array
  done
  exit 0
  curl \
    -v \
    -H "authorization: $AUTH" \
    -H "Content-Type: $MIME_TYPE" \
    -X PUT \
    -T "$FILE" \
    "$MCLI_ENDPOINT/file/1/$MCLI_TENANT/$MCLI_TAG/$SUBDIR/$FILE_NAME"
}

# Call the appropriate function if it's provided as an argument
if [ -n "$1" ]; then
  "$@"
fi
