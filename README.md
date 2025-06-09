# README | mcli

## OUT OF DATE -- TO UPDATE

## UNTIL THE README HAS BEEN UPDATED -- USE THE MAKEFILE

## Objective

The goal of `mcli` is to serve as a boostrapping template and home for your scripts.
Ultimately, it should be a 'build-your-own-mcli-script' engine. However, the core functionality
has not been finished.

## Core Functionality

- mcli provision interface
- mcli bundle interface
- mcli registry interface
- mcli script store
- Flexible: BYOS "Build Your Own Script" functionality.
- Extesible: CYOC "Create Your Own Command" functionality.

## Table of Contents

- [README | mcli](#readme--mcli)
  - [OUT OF DATE -- TO UPDATE](#out-of-date----to-update)
  - [UNTIL THE README HAS BEEN UPDATED -- USE THE MAKEFILE](#until-the-readme-has-been-updated----use-the-makefile)
  - [Objective](#objective)
  - [Core Functionality](#core-functionality)
  - [Table of Contents](#table-of-contents)
  - [Poetry](#poetry)
    - [Installation](#installation)
    - [Setting Up](#setting-up)
    - [Usage](#usage)
  - [Install `mcli`](#install-mcli)
  - [Usage](#usage-1)
  - [Features](#features)
  - [Dependencies](#dependencies)
  - [Contributing](#contributing)
  - [License](#license)
  - [Acknowledgments](#acknowledgments)
  - [Privacy | MOI](#privacy--moi)
    - [Adding Submodules](#adding-submodules)
    - [Initialize Submodules](#initialize-submodules)
    - [How It All Ties Together](#how-it-all-ties-together)

## Poetry

This project uses [Poetry](https://python-poetry.org/) for dependency management and packaging. Poetry makes it easy to build, package, and publish your Python projects. Here is how you can set it up:

### Installation

First, install Poetry. You can do this by following the instructions on the [official Poetry documentation](https://python-poetry.org/docs/#installation).

### Setting Up

After installing Poetry, you can set up the project by running:

```bash
poetry install
```

This command will install all the dependencies listed in the `pyproject.toml` file.

### Usage

You can use Poetry to manage dependencies, run scripts, and build the project. Here are some common commands:

- To add a new dependency:

  ```bash
  poetry add <package-name>
  ```

- To add a development dependency:

  ```bash
  poetry add --dev <package-name>
  ```

- To run the project:

  ```bash
  poetry run mcli
  ```

- To start an interactive shell within the project's virtual environment:

  ```bash
  poetry shell
  ```

- To build the project:

  ```bash
  poetry build
  ```

## Install `mcli`

To install `mcli`, ensure you have Python 3.10 or higher installed. You can use `pip` to install the package:

```bash
pip install dist/*.whl
```

Alternatively, you can install it directly from the source:

```bash
git clone https://github.com/mcli-e/mcliopen.git
cd open/mcli
pip install dist/*.whl
```

## Usage

`mcli` provides a command-line interface for managing your Python projects. To get started, use the following command:

```bash
mcli
```

You can find more detailed usage instructions in the [documentation](https://github.com/mcli-e/mcliopen.git).

## Features

- **Dependency Management**: Simplifies handling project dependencies using `poetry`.
- **Packaging**: Easy-to-use tools for building and distributing Python packages.
- **CLI Interface**: Command-line tools built with Python Click for efficient project management.
- **Cython Support**: Optionally compile Python code to C for improved performance.

## Dependencies

This project relies on several dependencies to provide its functionality. Key dependencies include:

- [requests](https://pypi.org/project/requests/): HTTP library for Python.
- [ipython](https://pypi.org/project/ipython/): Interactive computing in Python.
- [typer](https://pypi.org/project/typer/): Build great CLIs with Python.
- [click](https://pypi.org/project/click/): Python package for creating command-line interfaces.
- [cython](https://pypi.org/project/Cython/): C-Extensions for Python.
- [tensorflow](https://pypi.org/project/tensorflow/): Machine learning library.
- [flask](https://pypi.org/project/Flask/): Micro web framework.
- [keras](https://pypi.org/project/Keras/): Deep learning library.

For a complete list of dependencies, see the `pyproject.toml` file.

## Contributing

Contributions are welcome! Please read our [contributing guidelines](CONTRIBUTING.md) before submitting a pull request.

1. Fork the repository.
2. Create a new branch (`git checkout -b feature-branch`).
3. Make your changes.
4. Commit your changes (`git commit -am 'Add new feature'`).
5. Push to the branch (`git push origin feature-branch`).
6. Create a new Pull Request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgments

This project makes use of Python Click, a package for creating beautiful command-line interfaces in Python. Click is an open-source project maintained by the Pallets project. If you find Click useful, please consider [donating to the project](https://palletsprojects.com/donate) or contributing to its development.

Special thanks to all the contributors and open-source projects that make `mcli` possible.

## Privacy | MOI

### Adding Submodules

To add any private commands to the CLI, you must first add the submodule to your repository. Here's how you can do it:

1. **Add the Submodule:**

   ```bash
   git submodule add https://github.com/<repo_id>/<submodule_repo_name>/ src/cli/private/<submodule_repo_name>
   ```

2. **Commit the Changes:**  
   After adding the submodule, you’ll have changes in your working directory (including the new folder and the `.gitmodules` file). Stage and commit these changes:

   ```bash
   git add .gitmodules src/cli/private/<submodule_repo_name>
   git commit -m "Add submodule under src/cli/private/"
   ```

### Initialize Submodules

Initialize and update the submodule by running:

     ```bash
     git submodule update --init --recursive
     ```

- If you need to pull updates from the submodule’s remote repository, navigate into the submodule’s directory and run:

  ```bash
  git pull
  ```

  Alternatively, you can update the submodule in your main repository with:

  ```bash
  git submodule update --remote src/cli/private/<submodule_repo_name>
  ```

### How It All Ties Together

- **Submodules and .gitmodules:**  
  Adding a submodule registers an external repository within your main repository. The `.gitmodules` file keeps track of where the submodule is located and its source URL, which ensures that anyone else cloning your repository knows where to retrieve the submodule from.

- **Isolation of External Code:**  
  By placing the submodule inside `src/cli/private/`, you keep the external code organized within your project structure. This makes it clear which parts of your project are maintained externally versus your own code.

- **Versioning:**  
  The submodule is tied to a specific commit rather than a branch by default. This means that your repository remains stable even if the external repository makes further commits. You can always update to a newer commit when needed, ensuring a controlled integration.
