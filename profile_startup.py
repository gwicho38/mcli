#!/usr/bin/env python3
"""
MCLI Startup Profiling Script

This script profiles the startup time of MCLI to identify bottlenecks
and optimize performance.
"""

import time
import cProfile
import pstats
import io
import sys
import os
from pathlib import Path
import importlib
import tracemalloc

def profile_import_time():
    """Profile the time it takes to import MCLI modules"""
    print("🔍 Profiling MCLI Import Times...")
    print("=" * 50)
    
    modules_to_profile = [
        'mcli',
        'mcli.lib.api.mcli_decorators',
        'mcli.lib.api.api',
        'mcli.lib.api.daemon_decorator',
        'mcli.lib.logger.logger',
        'mcli.lib.toml.toml',
        'click',
        'fastapi',
        'uvicorn'
    ]
    
    import_times = {}
    
    for module_name in modules_to_profile:
        start_time = time.perf_counter()
        try:
            module = importlib.import_module(module_name)
            end_time = time.perf_counter()
            import_time = (end_time - start_time) * 1000  # Convert to milliseconds
            import_times[module_name] = import_time
            print(f"✅ {module_name}: {import_time:.2f}ms")
        except ImportError as e:
            print(f"❌ {module_name}: Import failed - {e}")
            import_times[module_name] = None
    
    return import_times

def profile_memory_usage():
    """Profile memory usage during MCLI import"""
    print("\n🧠 Profiling Memory Usage...")
    print("=" * 50)
    
    tracemalloc.start()
    
    # Import MCLI
    import mcli
    
    current, peak = tracemalloc.get_traced_memory()
    print(f"Current memory usage: {current / 1024 / 1024:.2f} MB")
    print(f"Peak memory usage: {peak / 1024 / 1024:.2f} MB")
    
    # Get top memory allocations
    snapshot = tracemalloc.take_snapshot()
    top_stats = snapshot.statistics('lineno')
    
    print("\nTop 10 memory allocations:")
    for stat in top_stats[:10]:
        print(f"  {stat.count} blocks: {stat.size / 1024:.1f} KB")
        print(f"    {stat.traceback.format()}")
    
    tracemalloc.stop()
    return current, peak

def profile_decorator_creation():
    """Profile the time it takes to create MCLI decorators"""
    print("\n🎨 Profiling Decorator Creation...")
    print("=" * 50)
    
    import mcli
    
    decorators_to_test = [
        ('@mcli.command()', lambda: mcli.command()),
        ('@mcli.group()', lambda: mcli.group()),
        ('@mcli.option()', lambda: mcli.option('--test')),
        ('@mcli.argument()', lambda: mcli.argument('test')),
    ]
    
    decorator_times = {}
    
    for name, decorator_func in decorators_to_test:
        start_time = time.perf_counter()
        try:
            decorator = decorator_func()
            end_time = time.perf_counter()
            creation_time = (end_time - start_time) * 1000000  # Convert to microseconds
            decorator_times[name] = creation_time
            print(f"✅ {name}: {creation_time:.2f}μs")
        except Exception as e:
            print(f"❌ {name}: Creation failed - {e}")
            decorator_times[name] = None
    
    return decorator_times

def profile_cli_creation():
    """Profile the time it takes to create a complete CLI"""
    print("\n⚡ Profiling CLI Creation...")
    print("=" * 50)
    
    import mcli
    
    start_time = time.perf_counter()
    
    @mcli.group()
    def testcli():
        pass
    
    @testcli.command()
    @mcli.option('--name', default='World')
    def greet(name: str):
        return f"Hello, {name}!"
    
    end_time = time.perf_counter()
    creation_time = (end_time - start_time) * 1000  # Convert to milliseconds
    
    print(f"✅ Complete CLI creation: {creation_time:.2f}ms")
    return creation_time

def profile_api_server_startup():
    """Profile the time it takes to start the API server"""
    print("\n🌐 Profiling API Server Startup...")
    print("=" * 50)
    
    import mcli
    
    start_time = time.perf_counter()
    
    try:
        server_url = mcli.start_server(host='127.0.0.1', port=8001, debug=False)
        startup_time = (time.perf_counter() - start_time) * 1000  # Convert to milliseconds
        print(f"✅ API server startup: {startup_time:.2f}ms")
        print(f"   Server URL: {server_url}")
        
        # Stop the server
        mcli.stop_server()
        
        return startup_time
    except Exception as e:
        print(f"❌ API server startup failed: {e}")
        return None

def profile_background_service():
    """Profile the time it takes to check background service availability"""
    print("\n🔄 Profiling Background Service...")
    print("=" * 50)
    
    import mcli
    
    start_time = time.perf_counter()
    
    try:
        is_available = mcli.is_background_available()
        check_time = (time.perf_counter() - start_time) * 1000  # Convert to milliseconds
        print(f"✅ Background service check: {check_time:.2f}ms")
        print(f"   Available: {is_available}")
        
        return check_time
    except Exception as e:
        print(f"❌ Background service check failed: {e}")
        return None

def run_detailed_profiling():
    """Run detailed profiling with cProfile"""
    print("\n📊 Running Detailed Profiling...")
    print("=" * 50)
    
    # Create a profiler
    pr = cProfile.Profile()
    pr.enable()
    
    # Import and use MCLI
    import mcli
    
    @mcli.group()
    def testcli():
        pass
    
    @testcli.command()
    @mcli.option('--name', default='World')
    def greet(name: str):
        return f"Hello, {name}!"
    
    # Check background service
    mcli.is_background_available()
    
    pr.disable()
    
    # Print stats
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
    ps.print_stats(20)  # Top 20 functions
    
    print("Top 20 functions by cumulative time:")
    print(s.getvalue())

def generate_performance_report():
    """Generate a comprehensive performance report"""
    print("🚀 MCLI Performance Profiling Report")
    print("=" * 60)
    
    # Run all profiling functions
    import_times = profile_import_time()
    current_mem, peak_mem = profile_memory_usage()
    decorator_times = profile_decorator_creation()
    cli_creation_time = profile_cli_creation()
    api_startup_time = profile_api_server_startup()
    background_check_time = profile_background_service()
    
    # Run detailed profiling
    run_detailed_profiling()
    
    # Generate summary
    print("\n📈 Performance Summary")
    print("=" * 60)
    
    total_import_time = sum(t for t in import_times.values() if t is not None)
    print(f"Total import time: {total_import_time:.2f}ms")
    print(f"Memory usage: {current_mem / 1024 / 1024:.2f} MB (peak: {peak_mem / 1024 / 1024:.2f} MB)")
    
    if cli_creation_time:
        print(f"CLI creation time: {cli_creation_time:.2f}ms")
    
    if api_startup_time:
        print(f"API server startup: {api_startup_time:.2f}ms")
    
    if background_check_time:
        print(f"Background service check: {background_check_time:.2f}ms")
    
    # Identify bottlenecks
    print("\n🔍 Potential Bottlenecks:")
    print("=" * 60)
    
    slow_imports = [(name, time) for name, time in import_times.items() if time and time > 100]
    if slow_imports:
        print("Slow imports (>100ms):")
        for name, time in slow_imports:
            print(f"  - {name}: {time:.2f}ms")
    
    slow_decorators = [(name, time) for name, time in decorator_times.items() if time and time > 1000]
    if slow_decorators:
        print("Slow decorator creation (>1000μs):")
        for name, time in slow_decorators:
            print(f"  - {name}: {time:.2f}μs")
    
    if total_import_time > 500:
        print(f"⚠️  Total import time is high: {total_import_time:.2f}ms")
    
    if current_mem > 50 * 1024 * 1024:  # 50MB
        print(f"⚠️  Memory usage is high: {current_mem / 1024 / 1024:.2f} MB")

if __name__ == "__main__":
    generate_performance_report() 