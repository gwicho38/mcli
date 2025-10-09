"""Debug Dependencies - Diagnostic page for troubleshooting installation issues"""

import streamlit as st
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple


def show_debug_dependencies():
    """Diagnostic page for dependency debugging"""

    st.title("🔍 Dependency Diagnostics")
    st.markdown("""
    This page helps diagnose why certain dependencies (like alpaca-py) may not be installing correctly.
    """)

    # Python environment info
    st.header("🐍 Python Environment")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Python Version", f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    with col2:
        st.metric("Platform", sys.platform)

    with st.expander("📋 Detailed Python Info", expanded=False):
        st.code(f"""
Python Version: {sys.version}
Python Path: {sys.executable}
Prefix: {sys.prefix}
Platform: {sys.platform}
        """)

    # Check Python paths
    st.header("📁 Python Paths")
    with st.expander("View all Python paths", expanded=False):
        for i, path in enumerate(sys.path, 1):
            st.code(f"{i}. {path}")

    # Test critical imports
    st.header("📦 Critical Import Tests")

    critical_imports = [
        ("streamlit", "Streamlit core"),
        ("pandas", "Data processing"),
        ("numpy", "Numerical computing"),
        ("plotly", "Visualizations"),
        ("requests", "HTTP requests"),
        ("supabase", "Database client"),
        ("yfinance", "Yahoo Finance API"),
        ("alpaca", "Alpaca Trading API - Main module"),
        ("alpaca.trading", "Alpaca Trading client"),
        ("alpaca.data", "Alpaca Data client"),
        ("alpaca.broker", "Alpaca Broker client"),
    ]

    import_results: List[Tuple[str, str, bool, str]] = []

    for module_name, description in critical_imports:
        try:
            module = __import__(module_name)
            version = getattr(module, "__version__", "Unknown")
            import_results.append((module_name, description, True, version))
        except ImportError as e:
            import_results.append((module_name, description, False, str(e)))
        except Exception as e:
            import_results.append((module_name, description, False, f"Unexpected error: {str(e)}"))

    # Display results in a nice table
    success_count = sum(1 for _, _, success, _ in import_results if success)
    fail_count = len(import_results) - success_count

    col1, col2 = st.columns(2)
    with col1:
        st.metric("✅ Successful Imports", success_count)
    with col2:
        st.metric("❌ Failed Imports", fail_count)

    st.markdown("---")

    for module_name, description, success, info in import_results:
        if success:
            with st.expander(f"✅ **{module_name}** - {description}", expanded=False):
                st.success(f"Successfully imported")
                st.code(f"Version: {info}")
        else:
            with st.expander(f"❌ **{module_name}** - {description}", expanded=True):
                st.error(f"Import failed")
                st.code(info)

    # Detailed alpaca-py investigation
    st.header("🔬 Alpaca-py Deep Dive")

    st.markdown("""
    Attempting to import alpaca-py components individually to identify specific failure points.
    """)

    alpaca_submodules = [
        "alpaca",
        "alpaca.common",
        "alpaca.trading",
        "alpaca.trading.client",
        "alpaca.trading.requests",
        "alpaca.trading.models",
        "alpaca.data",
        "alpaca.data.historical",
        "alpaca.broker",
    ]

    for submodule in alpaca_submodules:
        try:
            mod = __import__(submodule)
            st.success(f"✅ {submodule}")
            if hasattr(mod, "__file__"):
                st.caption(f"Location: {mod.__file__}")
        except ImportError as e:
            st.error(f"❌ {submodule}")
            with st.expander("Error details"):
                st.code(str(e))
        except Exception as e:
            st.warning(f"⚠️  {submodule}")
            with st.expander("Error details"):
                st.code(f"Unexpected error: {str(e)}")

    # List installed packages
    st.header("📋 Installed Packages")

    try:
        result = subprocess.run(
            ["pip", "list", "--format=columns"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            # Search for alpaca-related packages
            alpaca_packages = [
                line for line in result.stdout.split("\n")
                if "alpaca" in line.lower()
            ]

            if alpaca_packages:
                st.success("Found alpaca-related packages:")
                for pkg in alpaca_packages:
                    st.code(pkg)
            else:
                st.error("⚠️ No alpaca-related packages found in pip list!")

            with st.expander("📦 All Installed Packages (click to expand)"):
                st.code(result.stdout)
        else:
            st.error("Failed to run pip list")
            st.code(result.stderr)

    except subprocess.TimeoutExpired:
        st.error("pip list command timed out")
    except Exception as e:
        st.error(f"Error running pip list: {str(e)}")

    # Check for specific alpaca-py installation
    st.header("🔎 Alpaca-py Installation Check")

    try:
        result = subprocess.run(
            ["pip", "show", "alpaca-py"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            st.success("✅ alpaca-py package is installed!")
            st.code(result.stdout)

            # Try to get the version
            try:
                import alpaca
                if hasattr(alpaca, "__version__"):
                    st.info(f"Alpaca version from import: {alpaca.__version__}")
            except:
                pass
        else:
            st.error("❌ alpaca-py package NOT found!")
            st.code(result.stderr)

            # Suggest installation
            st.markdown("### 💡 Suggested Fix")
            st.code("pip install alpaca-py>=0.20.0", language="bash")

    except subprocess.TimeoutExpired:
        st.error("pip show command timed out")
    except Exception as e:
        st.error(f"Error running pip show: {str(e)}")

    # Check requirements.txt
    st.header("📄 Requirements.txt Check")

    requirements_path = Path(__file__).parent.parent.parent.parent.parent / "requirements.txt"

    if requirements_path.exists():
        with open(requirements_path, "r") as f:
            requirements_content = f.read()

        # Check if alpaca-py is in requirements
        if "alpaca-py" in requirements_content.lower():
            st.success("✅ alpaca-py found in requirements.txt")
        else:
            st.error("❌ alpaca-py NOT found in requirements.txt!")

        # Show relevant lines
        st.markdown("### Alpaca-related lines:")
        for line in requirements_content.split("\n"):
            if "alpaca" in line.lower() and not line.strip().startswith("#"):
                st.code(line)

        with st.expander("📋 Full requirements.txt"):
            st.code(requirements_content)
    else:
        st.warning(f"requirements.txt not found at {requirements_path}")

    # Environment variables check
    st.header("🔐 Environment Variables")

    env_vars_to_check = [
        "ALPACA_API_KEY",
        "ALPACA_SECRET_KEY",
        "ALPACA_BASE_URL",
        "PYTHONPATH",
        "PATH",
    ]

    st.markdown("Checking for relevant environment variables:")

    import os
    for var in env_vars_to_check:
        value = os.environ.get(var)
        if value:
            if "KEY" in var or "SECRET" in var:
                # Mask sensitive values
                masked = value[:4] + "..." + value[-4:] if len(value) > 8 else "***"
                st.success(f"✅ {var} = {masked}")
            else:
                with st.expander(f"✅ {var}", expanded=False):
                    st.code(value)
        else:
            st.info(f"ℹ️  {var} = Not set")

    # Streamlit Cloud specific checks
    st.header("☁️ Streamlit Cloud Detection")

    is_cloud = os.environ.get("STREAMLIT_RUNTIME_ENVIRONMENT") == "cloud"

    if is_cloud:
        st.success("✅ Running on Streamlit Cloud")
        st.info("""
        **Note:** On Streamlit Cloud, packages are installed from requirements.txt during deployment.
        If alpaca-py is not installed, check:
        1. requirements.txt has correct package name and version
        2. Package has no conflicting dependencies
        3. Deployment logs for installation errors
        """)
    else:
        st.info("ℹ️  Running locally (not Streamlit Cloud)")

    # System information
    st.header("💻 System Information")

    import platform

    sys_info = {
        "System": platform.system(),
        "Release": platform.release(),
        "Version": platform.version(),
        "Machine": platform.machine(),
        "Processor": platform.processor(),
        "Python Implementation": platform.python_implementation(),
        "Python Compiler": platform.python_compiler(),
    }

    for key, value in sys_info.items():
        st.text(f"{key}: {value}")

    # Troubleshooting guide
    st.header("🛠️ Troubleshooting Guide")

    with st.expander("🔧 Common Solutions", expanded=True):
        st.markdown("""
        ### If alpaca-py import fails:

        #### 1. Check Requirements.txt
        - Ensure `alpaca-py>=0.20.0` is present
        - No conflicting version constraints
        - No explicit sub-dependencies (websockets, msgpack, etc.)

        #### 2. Check Python Version
        - alpaca-py requires Python 3.8+
        - Best tested on Python 3.11
        - Create `.python-version` file with `3.11`

        #### 3. Dependency Conflicts
        - Remove explicit version pins for sub-dependencies
        - Let pip resolve dependencies automatically
        - Check for conflicts with other packages

        #### 4. Streamlit Cloud Deployment
        - Check deployment logs for installation errors
        - Verify requirements.txt is in repo root
        - Ensure no typos in package names
        - Check for timeout during installation

        #### 5. Alternative Approaches
        - Try pinning to specific version: `alpaca-py==0.20.0`
        - Try older stable version: `alpaca-py==0.15.0`
        - Check alpaca-py GitHub issues for known problems

        ### Debug Commands (local)
        ```bash
        # Verify installation
        pip show alpaca-py

        # Test import
        python -c "import alpaca; print(alpaca.__version__)"

        # Check for conflicts
        pip check

        # Reinstall clean
        pip uninstall alpaca-py -y
        pip install alpaca-py>=0.20.0
        ```
        """)

    # Export diagnostics
    st.header("💾 Export Diagnostics")

    if st.button("📋 Copy Diagnostics to Clipboard"):
        diagnostics = f"""
# Dependency Diagnostics Report
Generated: {pd.Timestamp.now()}

## Python Environment
- Version: {sys.version}
- Platform: {sys.platform}
- Executable: {sys.executable}

## Import Test Results
"""
        for module_name, description, success, info in import_results:
            status = "✅ SUCCESS" if success else "❌ FAILED"
            diagnostics += f"\n- {module_name}: {status}\n  Info: {info}\n"

        diagnostics += "\n## Installed Packages\n"
        if 'result' in locals() and result.returncode == 0:
            diagnostics += result.stdout

        st.code(diagnostics)
        st.success("Diagnostics generated! Copy the text above.")


if __name__ == "__main__":
    import pandas as pd
    show_debug_dependencies()
