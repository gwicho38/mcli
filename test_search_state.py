import requests
import time


def test_search_state_and_commands():
    search_url = 'http://127.0.0.1:5005/search_state'
    commands_url = 'http://127.0.0.1:5005/commands'
    # Wait a bit to let uptime increment
    time.sleep(2)
    queries = ['users', 'status', 'uptime', 'alice', 'running', 'bob']
    for query in queries:
        resp = requests.post(search_url, json={'query': query})
        print(f"Query: {query}")
        print("Response:", resp.json())
        print()
    # Show all available commands
    resp = requests.get(commands_url)
    print("All available commands:")
    print(resp.json())
    print()

if __name__ == '__main__':
    test_search_state_and_commands()
