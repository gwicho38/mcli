#!/usr/bin/env python3
"""Test script to verify all dashboard pages can be imported"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("Testing dashboard page imports...\n")

pages_to_test = [
    (
        "Predictions Enhanced",
        "mcli.ml.dashboard.pages.predictions_enhanced",
        "show_predictions_enhanced",
    ),
    ("Scrapers & Logs", "mcli.ml.dashboard.pages.scrapers_and_logs", "show_scrapers_and_logs"),
    ("Trading Dashboard", "mcli.ml.dashboard.pages.trading", "show_trading_dashboard"),
    ("Test Portfolio", "mcli.ml.dashboard.pages.test_portfolio", "show_test_portfolio"),
    (
        "Monte Carlo Predictions",
        "mcli.ml.dashboard.pages.monte_carlo_predictions",
        "show_monte_carlo_predictions",
    ),
    ("CI/CD Pipelines", "mcli.ml.dashboard.pages.cicd", "show_cicd_dashboard"),
    ("Workflows", "mcli.ml.dashboard.pages.workflows", "show_workflows_dashboard"),
]

results = []

for page_name, module_path, function_name in pages_to_test:
    try:
        module = __import__(module_path, fromlist=[function_name])
        func = getattr(module, function_name)
        if callable(func):
            results.append((page_name, "✅ SUCCESS", "Function is callable"))
        else:
            results.append((page_name, "⚠️  WARNING", "Function exists but not callable"))
    except ImportError as e:
        results.append((page_name, "❌ FAILED", f"Import error: {str(e)[:50]}"))
    except AttributeError as e:
        results.append((page_name, "❌ FAILED", f"Function not found: {str(e)[:50]}"))
    except Exception as e:
        results.append((page_name, "❌ FAILED", f"Unexpected error: {str(e)[:50]}"))

# Print results
print("=" * 80)
print(f"{'Page Name':<25} {'Status':<15} {'Details'}")
print("=" * 80)

success_count = 0
for page_name, status, details in results:
    print(f"{page_name:<25} {status:<15} {details}")
    if "SUCCESS" in status:
        success_count += 1

print("=" * 80)
print(f"\nResults: {success_count}/{len(pages_to_test)} pages can be imported successfully")

if success_count == len(pages_to_test):
    print("\n🎉 All pages are working!")
    sys.exit(0)
else:
    print(f"\n⚠️  {len(pages_to_test) - success_count} page(s) have issues")
    sys.exit(1)
