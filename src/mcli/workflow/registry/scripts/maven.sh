#!/bin/bash

# JSON file containing the dependencies
json_file="dependencies.json"

# Base URL for Maven repository
base_url=""

# Parse the JSON file and fetch each dependency
jq -r 'to_entries[] | .key + ":" + .value' $json_file | while IFS=":" read -r group_id artifact_id version; do
    # Replace '.' with '/' in group_id to match the Maven repository structure
    #     dependency=$(echo "$line" | cut -d ' ' -f 1)
    # version=$(echo "$line" | cut -d ' ' -f 2)
    group_path=$(echo $group_id | tr '.' '/')
    
    # Construct the file path for the dependency
    # file_path="$group_path/$artifact_id/$version/${artifact_id}-${version}.jar"
    file_path="$group_path/$artifact_id/$version/${artifact_id}-${version}.pom"
    # $file_path=$(echo $file_path | cut -d ' ' -f 1)
    file_path=$(echo $file_path | sed 's/://g')
    # echo $file_path
    
    # Construct the full URL for downloading the dependency
    full_url="$base_url/$file_path"
    # echo $request_url | sed 's/://g'
      
    
    echo "Downloading $artifact_id$version from $full_url"
    
    # Use wget to download the file
    wget $full_url -P ./dependencies/
done
