#!/usr/bin/env zsh

upload_to_confluence() {
  local build_name="$1"
  local build_path="${build_name}"

  # Check if necessary environment variables are set
  if [[ -z "$CONFLUENCE_PAT" ]]; then
    echo "Error: CONFLUENCE_PAT environment variable must be set"
    return 1
  fi

  # Check if file exists
  if [[ -f "$build_path" ]]; then
    echo "Found build file: $build_path"
  
    # Get file size
    local file_size=$(du -h "$build_path" | cut -f1)
    echo "File size: $file_size"

    # Confluence page ID from your URL
    local page_id="9466314982"
    local domain="mclienergy.atlassian.net"

    # Create a temporary file to store the response
    local response_file=$(mktemp)

    echo "Uploading to Confluence..."

    # Use the exact format from the valid request, but capture the response
    local confluence_user="${CONFLUENCE_USER}" # your email address
    local confluence_token="${CONFLUENCE_PAT}" # your API token

    curl --request POST \
      --user "${confluence_user}:${confluence_token}" \
      --header "Accept: application/json" \
      --header "X-Atlassian-Token: no-check" \
      --form "file=@${build_path}" \
      --output "${response_file}" \
      "https://${domain}/wiki/rest/api/content/${page_id}/child/attachment"

    # Check curl exit status
    local curl_status=$?

    # Read the response content
    local response_content=$(cat "${response_file}")

    # Check if the response contains an error
    if [[ $curl_status -eq 0 && ! "$response_content" == *"error"* ]]; then
      echo "Successfully uploaded ${build_name} to Confluence"
      rm -f "${response_file}" # Clean up
      return 0
    else
      echo "Failed to upload ${build_name} to Confluence"
      if [[ $curl_status -ne 0 ]]; then
        echo "Curl exit code: ${curl_status}"
      fi
      echo "Response content:"
      echo "$response_content"

      # Look for specific errors
      if [[ "$response_content" == *"Failed to parse Connect Session Auth Token"* ]]; then
        echo "Authentication error: The token format may be incorrect."
        echo "Make sure you're using the correct PAT format. Try without the 'Bearer' prefix."
      fi

      rm -f "${response_file}" # Clean up
      return 1
    fi
  else
    echo "Error: Build file does not exist: $build_path"
    return 1
  fi
}
