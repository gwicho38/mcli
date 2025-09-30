#!/usr/bin/env python3
"""
Test script to verify personal assistant agent functionality
"""

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_agent_routing():
    """Test the personal assistant routing logic"""
    
    from mcli.chat.chat import ChatClient
    
    # Create chat client
    client = ChatClient()
    
    test_queries = [
        ("what's my status?", "Job management - agent status"),
        ("list my jobs", "Job management - list jobs"),
        ("schedule cleanup daily", "Job management - scheduling"),
        ("remind me to check disk space", "Job management - reminder"),
        ("how much disk space do I have?", "System control - disk info"),
        ("can you help me free up space?", "System help request"),
        ("what time is it?", "System control - time"),
        ("cancel my cleanup job", "Job management - cancellation"),
        ("show me system specs", "System control - info"),
        ("what can you do for me?", "General query")
    ]
    
    print("Testing Personal Assistant Agent Routing")
    print("=" * 50)
    
    for query, expected in test_queries:
        print(f"\n🔍 Query: '{query}'")
        print(f"📋 Expected: {expected}")
        print("-" * 40)
        
        # Test routing logic
        is_system = client.is_system_control_request(query)
        is_job = client._is_job_management_request(query)
        is_help = client._is_system_help_request(query)
        
        if is_job:
            route = "Job Management"
        elif is_system:
            route = "System Control"
        elif is_help:
            route = "System Help"
        else:
            route = "LLM Response"
        
        print(f"✅ Routed to: {route}")
        
        # Show detection details
        print(f"   System: {is_system}, Job: {is_job}, Help: {is_help}")
    
    print("\n" + "=" * 50)
    print("Agent routing test completed!")

def test_agent_context():
    """Test agent context awareness"""
    
    print("\nTesting Agent Context Awareness")
    print("=" * 40)
    
    try:
        from mcli.workflow.scheduler.persistence import JobPersistence
        from mcli.workflow.scheduler.job import Job, JobStatus
        
        # Check job persistence
        persistence = JobPersistence()
        jobs = persistence.load_jobs()
        
        print(f"📅 Jobs in persistence: {len(jobs)}")
        
        # Show job status breakdown
        if jobs:
            status_counts = {}
            for job_data in jobs:
                status = job_data.get("status", "unknown")
                status_counts[status] = status_counts.get(status, 0) + 1
            
            for status, count in status_counts.items():
                print(f"   {status}: {count}")
        
        print("✅ Job system accessible")
        
    except Exception as e:
        print(f"❌ Job system error: {e}")
    
    try:
        from mcli.chat.system_controller import system_controller
        
        # Test system info access
        result = system_controller.get_memory_usage()
        if result.get("success"):
            mem = result["data"]["virtual_memory"]
            print(f"💾 Memory access: {mem['usage_percent']:.1f}% used")
            print("✅ System control accessible")
        else:
            print("❌ System control failed")
            
    except Exception as e:
        print(f"❌ System control error: {e}")

if __name__ == "__main__":
    test_agent_routing()
    test_agent_context()