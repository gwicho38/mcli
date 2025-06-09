def read_from_toml(file_path: str, key: str):
    """
    Reads a TOML file and returns the value associated with the provided key.

    Args:
        file_path (str): The path to the TOML file.
        key (str): The key whose value will be retrieved.

    Returns:
        The value corresponding to the key if it exists in the TOML file, or None otherwise.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        tomllib.TOMLDecodeError or toml.TomlDecodeError: If the file contains invalid TOML.
    """
    try:
        # Attempt to use the built-in tomllib (available in Python 3.11+)
        import tomllib

        with open(file_path, "rb") as file:
            config_data = tomllib.load(file)
    except ModuleNotFoundError:
        # Fall back to the third-party 'toml' package for earlier Python versions.
        import toml

        with open(file_path, "r", encoding="utf-8") as file:
            config_data = toml.load(file)

    # Return the value for the provided key, or None if the key is not found.
    return config_data.get(key)


__all__ = ["read_from_toml"]
