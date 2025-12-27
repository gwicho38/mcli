#!/usr/bin/env python3
"""Feature detection utilities for conditional imports."""

import os
from typing import Set


def has_ml_features() -> bool:
    """Check if user is actually using ML features."""
    return os.getenv("MCLI_ENABLE_ML", "").lower() in ("true", "1", "yes") or _check_ml_imports()


def has_dashboard_features() -> bool:
    """Check if user is actually using dashboard features."""
    return (
        os.getenv("MCLI_ENABLE_DASHBOARD", "").lower() in ("true", "1", "yes")
        or _check_dashboard_imports()
    )


def has_trading_features() -> bool:
    """Check if user is actually using trading features."""
    return (
        os.getenv("MCLI_ENABLE_TRADING", "").lower() in ("true", "1", "yes")
        or _check_trading_imports()
    )


def _check_ml_imports() -> bool:
    """Check if ML libraries are already imported."""
    try:
        import sys

        ml_modules = {"torch", "tensorflow", "scikit_learn", "mlflow"}
        return any(module in sys.modules for module in ml_modules)
    except ImportError:
        return False


def _check_dashboard_imports() -> bool:
    """Check if dashboard libraries are already imported."""
    try:
        import sys

        dashboard_modules = {"streamlit", "plotly", "matplotlib"}
        return any(module in sys.modules for module in dashboard_modules)
    except ImportError:
        return False


def _check_trading_imports() -> bool:
    """Check if trading libraries are already imported."""
    try:
        import sys

        trading_modules = {"pandas", "yfinance", "alpha_vantage"}
        return any(module in sys.modules for module in trading_modules)
    except ImportError:
        return False


def get_required_features() -> Set[str]:
    """Get set of features required based on current command/usage."""
    features = set()

    # Check command line arguments
    import sys

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd in ["train", "predict", "mlflow", "experiment"]:
            features.add("ml")
        elif cmd in ["dashboard", "viz", "plot"]:
            features.add("dashboard")
        elif cmd in ["trade", "backtest", "portfolio", "optimize"]:
            features.add("trading")

    return features
