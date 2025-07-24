#!/bin/bash
"""
MCLI Performance Profiling Script

This script runs comprehensive performance profiling on MCLI to identify
bottlenecks and optimize startup time.
"""

set -e

echo "🚀 MCLI Performance Profiling"
echo "=============================="

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: Not in MCLI project directory"
    exit 1
fi

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "🔧 Activating virtual environment..."
    source .venv/bin/activate
fi

# Build wheel and binary if they don't exist
echo "📦 Building wheel and binary for profiling..."
make wheel
make binary

# Run startup profiling
echo ""
echo "🔍 Running Startup Profiling..."
python profile_startup.py

echo ""
echo "📊 Running Binary and Wheel Profiling..."
python profile_binary_wheel.py

# Generate summary report
echo ""
echo "📈 Generating Summary Report..."
echo "=============================="

if [ -f "profiling_results.json" ]; then
    echo "✅ Profiling results saved to profiling_results.json"
    echo ""
    echo "📋 Quick Summary:"
    echo "================="
    
    # Extract key metrics from JSON
    if command -v jq >/dev/null 2>&1; then
        echo "Python module import time: $(jq -r '.python_module.average // "N/A"' profiling_results.json)ms"
        echo "Binary help command time: $(jq -r '.binary.help_command.average // "N/A"' profiling_results.json)ms"
        echo "Wheel installation time: $(jq -r '.wheel.install_time // "N/A"' profiling_results.json)ms"
        
        click_time=$(jq -r '.comparison.click.average // "N/A"' profiling_results.json)
        mcli_time=$(jq -r '.comparison.mcli.average // "N/A"' profiling_results.json)
        
        if [ "$click_time" != "N/A" ] && [ "$mcli_time" != "N/A" ]; then
            echo "Click import time: ${click_time}ms"
            echo "MCLI import time: ${mcli_time}ms"
            
            # Calculate overhead
            overhead=$(echo "$mcli_time - $click_time" | bc -l 2>/dev/null || echo "N/A")
            if [ "$overhead" != "N/A" ]; then
                echo "MCLI overhead: ${overhead}ms"
            fi
        fi
    else
        echo "Install jq for detailed JSON parsing"
        echo "Results available in profiling_results.json"
    fi
else
    echo "❌ No profiling results found"
fi

echo ""
echo "🎉 Profiling complete!"
echo ""
echo "💡 Next Steps:"
echo "=============="
echo "1. Review profiling_results.json for detailed metrics"
echo "2. Check profile_startup.py output for import bottlenecks"
echo "3. Optimize slow imports or dependencies"
echo "4. Consider lazy loading for heavy modules"
echo "5. Re-run profiling after optimizations" 