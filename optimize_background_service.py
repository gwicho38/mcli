#!/usr/bin/env python3
"""
MCLI Background Service Optimization

This script optimizes the background service availability check to reduce
startup time from 2+ seconds to under 100ms.
"""

import time
import socket
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

def quick_port_check(host, port, timeout=0.1):
    """Quick port availability check"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False

def optimized_background_check():
    """Optimized background service availability check"""
    print("🔧 Optimizing Background Service Check...")
    print("=" * 50)
    
    # Test current implementation
    print("Current implementation:")
    start_time = time.perf_counter()
    
    import mcli
    is_available = mcli.is_background_available()
    
    current_time = (time.perf_counter() - start_time) * 1000
    print(f"  Time: {current_time:.2f}ms")
    print(f"  Available: {is_available}")
    
    # Test optimized implementation
    print("\nOptimized implementation:")
    start_time = time.perf_counter()
    
    # Quick port check instead of full HTTP request
    is_available_optimized = quick_port_check('localhost', 8000, timeout=0.1)
    
    optimized_time = (time.perf_counter() - start_time) * 1000
    print(f"  Time: {optimized_time:.2f}ms")
    print(f"  Available: {is_available_optimized}")
    
    # Calculate improvement
    improvement = current_time - optimized_time
    improvement_percent = (improvement / current_time) * 100
    
    print(f"\n📈 Improvement: {improvement:.2f}ms ({improvement_percent:.1f}%)")
    
    return {
        'current_time': current_time,
        'optimized_time': optimized_time,
        'improvement': improvement,
        'improvement_percent': improvement_percent
    }

def test_concurrent_checks():
    """Test concurrent background service checks"""
    print("\n🔄 Testing Concurrent Checks...")
    print("=" * 50)
    
    def check_service():
        import mcli
        return mcli.is_background_available()
    
    # Test sequential checks
    print("Sequential checks:")
    start_time = time.perf_counter()
    
    results = []
    for i in range(3):
        result = check_service()
        results.append(result)
    
    sequential_time = (time.perf_counter() - start_time) * 1000
    print(f"  Time: {sequential_time:.2f}ms")
    print(f"  Results: {results}")
    
    # Test concurrent checks
    print("\nConcurrent checks:")
    start_time = time.perf_counter()
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(check_service) for _ in range(3)]
        results = [future.result() for future in as_completed(futures)]
    
    concurrent_time = (time.perf_counter() - start_time) * 1000
    print(f"  Time: {concurrent_time:.2f}ms")
    print(f"  Results: {results}")
    
    # Calculate improvement
    improvement = sequential_time - concurrent_time
    improvement_percent = (improvement / sequential_time) * 100
    
    print(f"\n📈 Concurrent improvement: {improvement:.2f}ms ({improvement_percent:.1f}%)")

def create_optimized_implementation():
    """Create an optimized background service check implementation"""
    print("\n⚡ Creating Optimized Implementation...")
    print("=" * 50)
    
    optimized_code = '''
def is_background_available_optimized():
    """
    Optimized background service availability check.
    
    This implementation uses a quick port check instead of a full HTTP request,
    reducing startup time from 2+ seconds to under 100ms.
    """
    import socket
    import time
    
    def quick_port_check(host, port, timeout=0.1):
        """Quick port availability check"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except:
            return False
    
    # Check common background service ports
    ports_to_check = [8000, 8001, 8002, 9000, 9001]
    
    for port in ports_to_check:
        if quick_port_check('localhost', port, timeout=0.05):
            return True
    
    return False
'''
    
    print("Optimized implementation:")
    print(optimized_code)
    
    # Test the optimized implementation
    print("\nTesting optimized implementation:")
    start_time = time.perf_counter()
    
    # Execute the optimized code
    exec(optimized_code)
    is_available = locals()['is_background_available_optimized']()
    
    optimized_time = (time.perf_counter() - start_time) * 1000
    print(f"  Time: {optimized_time:.2f}ms")
    print(f"  Available: {is_available}")
    
    return optimized_code

def generate_optimization_report():
    """Generate a comprehensive optimization report"""
    print("🚀 MCLI Background Service Optimization Report")
    print("=" * 60)
    
    # Run optimization tests
    optimization_results = optimized_background_check()
    test_concurrent_checks()
    optimized_code = create_optimized_implementation()
    
    # Generate recommendations
    print("\n💡 Optimization Recommendations")
    print("=" * 50)
    
    if optimization_results['improvement_percent'] > 90:
        print("✅ Excellent optimization potential!")
        print(f"   Can reduce background check time by {optimization_results['improvement_percent']:.1f}%")
        print("   Recommendation: Implement quick port check")
    elif optimization_results['improvement_percent'] > 50:
        print("📈 Good optimization potential!")
        print(f"   Can reduce background check time by {optimization_results['improvement_percent']:.1f}%")
        print("   Recommendation: Consider implementing quick port check")
    else:
        print("⚠️  Limited optimization potential")
        print("   Consider other optimization strategies")
    
    print("\n🔧 Implementation Steps:")
    print("1. Replace HTTP request with quick port check")
    print("2. Use shorter timeout (0.1s instead of 2s)")
    print("3. Check multiple common ports")
    print("4. Cache results for short period")
    print("5. Make background service optional")
    
    print("\n📊 Expected Results:")
    print(f"- Current background check: {optimization_results['current_time']:.2f}ms")
    print(f"- Optimized background check: {optimization_results['optimized_time']:.2f}ms")
    print(f"- Total startup improvement: {optimization_results['improvement']:.2f}ms")
    print(f"- Overall startup time: ~{optimization_results['current_time'] - optimization_results['improvement']:.2f}ms")

if __name__ == "__main__":
    generate_optimization_report() 