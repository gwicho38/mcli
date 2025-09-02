import base64
import hashlib
import os

from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)

IN_MEMORY_FILE_FINGERPRINTS = {}
NO_CHANGE_TO_FILE = -1


def encode_content(path):
    """Encode file content and track changes using MD5 fingerprints"""
    logger.debug(f"encode_content: {path}")

    try:
        with open(path, "rb") as file:
            content = file.read()

        # Calculate MD5 fingerprint
        fingerprint = hashlib.md5(content).hexdigest()

        # Check if file has changed
        if IN_MEMORY_FILE_FINGERPRINTS.get(path) != fingerprint:
            IN_MEMORY_FILE_FINGERPRINTS[path] = fingerprint
            return base64.b64encode(content).decode("utf-8")
        else:
            return NO_CHANGE_TO_FILE

    except Exception as e:
        logger.error(f"Error encoding content from {path}: {e}")
        return NO_CHANGE_TO_FILE


def merge_txt_files(folder_path, file_type=".mcli", output_file="merged_output.txt"):
    """
    Recursively merge .mcli files from the given folder and its subdirectories.

    Args:
        folder_path (str): Path to the folder to start merging from
        output_file (str, optional): Name of the output merged file. Defaults to 'merged_output.txt'.
    """
    # Collect all .mcli files recursively
    mcli_files = []
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith(file_type):
                mcli_files.append(os.path.join(root, file))

    # Sort files to ensure consistent ordering
    mcli_files.sort()

    # Open the output file and write contents
    with open(output_file, "w", encoding="utf-8") as outfile:
        for filepath in mcli_files:
            try:
                # Add a header to identify the source file
                filename = os.path.basename(filepath)
                outfile.write(f"\n--- Content from {filename} ---\n")

                # Read and write content from the file
                with open(filepath, "r", encoding="utf-8") as infile:
                    outfile.write(infile.read())
                    outfile.write("\n")  # Add a newline between files
            except Exception as e:
                logger.info(f"Error reading {filepath}: {str(e)}")

    logger.info(f"Merged {len(mcli_files)} files into {output_file}")


if __name__ == "__main__":
    # Example usage
    print("File utilities module")
    print("Use encode_content() to track file changes")
    print("Use merge_txt_files() to merge files of a specific type")
