#!/usr/bin/env python3
"""
MCLI Binary and Wheel Performance Profiling

This script profiles the startup time of MCLI binary and wheel to identify
bottlenecks and optimize performance.
"""

import time
import subprocess
import sys
import os
from pathlib import Path
import json
import statistics

def measure_startup_time(command, iterations=5):
    """Measure the startup time of a command"""
    times = []
    
    for i in range(iterations):
        start_time = time.perf_counter()
        
        try:
            # Run the command and capture output
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=30  # 30 second timeout
            )
            
            end_time = time.perf_counter()
            execution_time = (end_time - start_time) * 1000  # Convert to milliseconds
            
            if result.returncode == 0:
                times.append(execution_time)
                print(f"  Run {i+1}: {execution_time:.2f}ms")
            else:
                print(f"  Run {i+1}: Failed (return code {result.returncode})")
                print(f"    Error: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            print(f"  Run {i+1}: Timeout (>30s)")
        except Exception as e:
            print(f"  Run {i+1}: Error - {e}")
    
    if times:
        avg_time = statistics.mean(times)
        min_time = min(times)
        max_time = max(times)
        std_dev = statistics.stdev(times) if len(times) > 1 else 0
        
        return {
            'times': times,
            'average': avg_time,
            'min': min_time,
            'max': max_time,
            'std_dev': std_dev,
            'successful_runs': len(times)
        }
    else:
        return None

def profile_python_module():
    """Profile MCLI as a Python module"""
    print("🐍 Profiling MCLI as Python Module...")
    print("=" * 50)
    
    command = [sys.executable, '-c', 'import mcli; print("MCLI imported successfully")']
    
    result = measure_startup_time(command)
    
    if result:
        print(f"✅ Average startup time: {result['average']:.2f}ms")
        print(f"   Min: {result['min']:.2f}ms, Max: {result['max']:.2f}ms")
        print(f"   Std Dev: {result['std_dev']:.2f}ms")
        print(f"   Successful runs: {result['successful_runs']}/5")
    else:
        print("❌ All runs failed")
    
    return result

def profile_wheel_installation():
    """Profile MCLI wheel installation and import"""
    print("\n📦 Profiling MCLI Wheel Installation...")
    print("=" * 50)
    
    # Check if wheel exists
    wheel_files = list(Path('.').glob('dist/*.whl'))
    
    if not wheel_files:
        print("❌ No wheel files found in dist/")
        print("   Run 'make wheel' to build the wheel first")
        return None
    
    wheel_file = wheel_files[0]
    print(f"📦 Found wheel: {wheel_file}")
    
    # Install wheel in a temporary environment
    install_command = [
        sys.executable, '-m', 'pip', 'install', 
        '--force-reinstall', '--no-deps', str(wheel_file)
    ]
    
    print("Installing wheel...")
    start_time = time.perf_counter()
    
    try:
        result = subprocess.run(install_command, capture_output=True, text=True)
        install_time = (time.perf_counter() - start_time) * 1000
        
        if result.returncode == 0:
            print(f"✅ Wheel installation: {install_time:.2f}ms")
        else:
            print(f"❌ Wheel installation failed: {result.stderr}")
            return None
    except Exception as e:
        print(f"❌ Wheel installation error: {e}")
        return None
    
    # Test import after installation
    import_command = [sys.executable, '-c', 'import mcli; print("MCLI imported successfully")']
    import_result = measure_startup_time(import_command)
    
    return {
        'install_time': install_time,
        'import_time': import_result
    }

def profile_binary_execution():
    """Profile MCLI binary execution"""
    print("\n🔧 Profiling MCLI Binary Execution...")
    print("=" * 50)
    
    # Check if binary exists
    binary_files = list(Path('.').glob('dist/*'))
    binary_files = [f for f in binary_files if f.is_file() and os.access(f, os.X_OK)]
    
    if not binary_files:
        print("❌ No executable binary found in dist/")
        print("   Run 'make binary' to build the binary first")
        return None
    
    binary_file = binary_files[0]
    print(f"🔧 Found binary: {binary_file}")
    
    # Test basic help command
    help_command = [str(binary_file), '--help']
    help_result = measure_startup_time(help_command)
    
    if help_result:
        print(f"✅ Binary help command: {help_result['average']:.2f}ms")
    
    # Test version command
    version_command = [str(binary_file), '--version']
    version_result = measure_startup_time(version_command)
    
    if version_result:
        print(f"✅ Binary version command: {version_result['average']:.2f}ms")
    
    return {
        'help_command': help_result,
        'version_command': version_result
    }

def profile_with_detailed_timing():
    """Profile with detailed timing information"""
    print("\n⏱️  Detailed Timing Analysis...")
    print("=" * 50)
    
    # Test different import scenarios
    scenarios = [
        ('Basic import', 'import mcli'),
        ('Import with decorators', 'import mcli; mcli.command()'),
        ('Import with API', 'import mcli; mcli.start_server()'),
        ('Import with background', 'import mcli; mcli.is_background_available()'),
    ]
    
    for name, code in scenarios:
        command = [sys.executable, '-c', f'{code}; print("Success")']
        result = measure_startup_time(command, iterations=3)
        
        if result:
            print(f"✅ {name}: {result['average']:.2f}ms")
        else:
            print(f"❌ {name}: Failed")

def compare_with_click():
    """Compare MCLI performance with pure Click"""
    print("\n⚖️  Comparing with Pure Click...")
    print("=" * 50)
    
    # Test pure Click
    click_command = [sys.executable, '-c', 'import click; print("Click imported successfully")']
    click_result = measure_startup_time(click_command)
    
    if click_result:
        print(f"✅ Pure Click: {click_result['average']:.2f}ms")
    
    # Test MCLI
    mcli_command = [sys.executable, '-c', 'import mcli; print("MCLI imported successfully")']
    mcli_result = measure_startup_time(mcli_command)
    
    if mcli_result:
        print(f"✅ MCLI: {mcli_result['average']:.2f}ms")
        
        if click_result:
            overhead = mcli_result['average'] - click_result['average']
            overhead_percent = (overhead / click_result['average']) * 100
            print(f"📊 Overhead: {overhead:.2f}ms ({overhead_percent:.1f}%)")
    
    return {
        'click': click_result,
        'mcli': mcli_result
    }

def generate_optimization_recommendations(results):
    """Generate optimization recommendations based on profiling results"""
    print("\n💡 Optimization Recommendations")
    print("=" * 50)
    
    recommendations = []
    
    # Check import times
    if 'python_module' in results and results['python_module']:
        import_time = results['python_module']['average']
        if import_time > 500:
            recommendations.append(f"⚠️  Import time is high ({import_time:.2f}ms). Consider lazy loading.")
        elif import_time > 200:
            recommendations.append(f"📝 Import time is moderate ({import_time:.2f}ms). Could be optimized.")
    
    # Check binary performance
    if 'binary' in results and results['binary']:
        help_time = results['binary']['help_command']['average'] if results['binary']['help_command'] else 0
        if help_time > 1000:
            recommendations.append(f"⚠️  Binary startup is slow ({help_time:.2f}ms). Consider static linking.")
    
    # Check wheel installation
    if 'wheel' in results and results['wheel']:
        install_time = results['wheel']['install_time']
        if install_time > 5000:
            recommendations.append(f"⚠️  Wheel installation is slow ({install_time:.2f}ms). Consider smaller dependencies.")
    
    # Check overhead vs Click
    if 'comparison' in results and results['comparison']:
        click_time = results['comparison']['click']['average'] if results['comparison']['click'] else 0
        mcli_time = results['comparison']['mcli']['average'] if results['comparison']['mcli'] else 0
        if click_time and mcli_time:
            overhead = mcli_time - click_time
            if overhead > 200:
                recommendations.append(f"⚠️  High overhead vs Click ({overhead:.2f}ms). Optimize imports.")
    
    if not recommendations:
        recommendations.append("✅ Performance looks good! No major optimizations needed.")
    
    for rec in recommendations:
        print(rec)

def save_results(results, filename='profiling_results.json'):
    """Save profiling results to JSON file"""
    # Convert results to JSON-serializable format
    json_results = {}
    
    for key, value in results.items():
        if value is None:
            json_results[key] = None
        elif isinstance(value, dict):
            json_results[key] = value
        else:
            json_results[key] = str(value)
    
    with open(filename, 'w') as f:
        json.dump(json_results, f, indent=2)
    
    print(f"\n💾 Results saved to {filename}")

def main():
    """Main profiling function"""
    print("🚀 MCLI Binary and Wheel Performance Profiling")
    print("=" * 60)
    
    results = {}
    
    # Run all profiling tests
    results['python_module'] = profile_python_module()
    results['wheel'] = profile_wheel_installation()
    results['binary'] = profile_binary_execution()
    results['detailed_timing'] = profile_with_detailed_timing()
    results['comparison'] = compare_with_click()
    
    # Generate recommendations
    generate_optimization_recommendations(results)
    
    # Save results
    save_results(results)
    
    print("\n🎉 Profiling complete!")

if __name__ == "__main__":
    main() 