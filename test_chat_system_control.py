#!/usr/bin/env python3
"""
Test Chat System Control
Demonstrates how MCLI chat can control system applications directly
"""

import json
import sys
import os

# Add src to path
sys.path.insert(0, 'src')

from mcli.chat.system_integration import handle_system_request, get_system_capabilities


def demo_chat_system_control():
    """Demonstrate chat-based system control"""
    
    print("🤖 MCLI Chat System Control Demo")
    print("=" * 50)
    print("This demonstrates how MCLI chat can control your system directly!")
    print()
    
    # Show available capabilities
    capabilities = get_system_capabilities()
    print("📋 Available System Functions:")
    for func_name, func_info in capabilities["functions"].items():
        print(f"  • {func_name}: {func_info['description']}")
    print()
    
    # Test examples
    test_requests = [
        "Open TextEdit and write Hello, World!",
        "Open TextEdit and write 'This is a test from MCLI chat' and save as test.txt",
        "Take a screenshot",
        "Open Calculator",
        "Open https://google.com",
        "Run date command"
    ]
    
    print("🧪 Testing System Control Requests:")
    print()
    
    for request in test_requests:
        print(f"👤 User: {request}")
        
        try:
            result = handle_system_request(request)
            
            if result["success"]:
                print(f"🤖 Assistant: {result.get('message', 'Done!')}")
                if result.get('output'):
                    print(f"   Output: {result['output'].strip()}")
            else:
                print(f"❌ Error: {result.get('error', 'Unknown error')}")
                if result.get('suggestion'):
                    print(f"💡 Suggestion: {result['suggestion']}")
            
        except Exception as e:
            print(f"❌ Exception: {e}")
        
        print()
    
    print("🎯 Interactive Mode")
    print("Type system control requests (or 'quit' to exit):")
    print("Examples:")
    print("  - 'Open TextEdit and write Hello World'")
    print("  - 'Take a screenshot'")
    print("  - 'Open Calculator'")
    print()
    
    while True:
        try:
            user_input = input("👤 You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            
            if not user_input:
                continue
            
            # Check if this looks like a system request
            system_keywords = [
                'open', 'close', 'write', 'textedit', 'screenshot', 
                'run', 'execute', 'launch', 'quit', 'calculator'
            ]
            
            if any(keyword in user_input.lower() for keyword in system_keywords):
                # Handle as system request
                result = handle_system_request(user_input)
                
                if result["success"]:
                    print(f"🤖 Assistant: {result.get('message', 'Done!')}")
                    if result.get('output'):
                        output_lines = result['output'].strip().split('\n')
                        for line in output_lines[:5]:  # Show first 5 lines
                            print(f"   {line}")
                        if len(output_lines) > 5:
                            print(f"   ... ({len(output_lines) - 5} more lines)")
                else:
                    print(f"🤖 Assistant: Sorry, I couldn't do that. {result.get('error', '')}")
                    if result.get('suggestion'):
                        print(f"💡 Try: {result['suggestion']}")
            else:
                print("🤖 Assistant: That doesn't look like a system control request.")
                print("   Try something like 'Open TextEdit and write Hello' or 'Take a screenshot'")
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


def quick_test():
    """Quick test of the TextEdit functionality"""
    print("🚀 Quick Test: Opening TextEdit and writing 'Hello, World!'")
    
    result = handle_system_request("Open TextEdit and write Hello, World!")
    
    if result["success"]:
        print("✅ Success! TextEdit should now be open with 'Hello, World!' text")
        print(f"📝 Details: {result.get('message', '')}")
    else:
        print(f"❌ Failed: {result.get('error', 'Unknown error')}")
    
    return result["success"]


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        quick_test()
    else:
        demo_chat_system_control()