import requests
import readline
import sys

API_URL = 'http://127.0.0.1:5005'

# Fetch available commands for slash menu
def fetch_commands():
    try:
        resp = requests.get(f'{API_URL}/commands')
        return resp.json().get('commands', [])
    except Exception:
        return []

def execute_command(name):
    resp = requests.post(f'{API_URL}/commands/{name}/execute')
    result = resp.json()
    print(f"[Command: {name}] Return code: {result.get('returncode')}")
    print(result.get('stdout', ''))
    if result.get('stderr'):
        print('stderr:', result['stderr'])

def chat():
    print("Welcome to the MCLI Chat Terminal. Type / to see available commands.")
    commands = fetch_commands()
    while True:
        try:
            user_input = input('You: ')
            if user_input.strip() == '/':
                # Show available commands
                commands = fetch_commands()
                if not commands:
                    print("No commands available.")
                    continue
                print("Available commands:")
                for idx, cmd in enumerate(commands):
                    print(f"  {idx+1}. /{cmd}")
                sel = input("Select command by number or name (or press Enter to cancel): ").strip()
                if not sel:
                    continue
                if sel.isdigit() and 1 <= int(sel) <= len(commands):
                    cmd_name = commands[int(sel)-1]
                else:
                    cmd_name = sel.lstrip('/')
                    if cmd_name not in commands:
                        print("Invalid command.")
                        continue
                execute_command(cmd_name)
            elif user_input.startswith('/'):
                cmd_name = user_input[1:]
                if cmd_name in commands:
                    execute_command(cmd_name)
                else:
                    print("Unknown command. Type / to see available commands.")
            elif user_input.lower() in {'exit', 'quit'}:
                print("Goodbye!")
                break
            else:
                # Send as chat message
                resp = requests.post(f'{API_URL}/v1/chat/completions', json={
                    'messages': [
                        {'role': 'user', 'content': user_input}
                    ]
                })
                data = resp.json()
                reply = data['choices'][0]['message']['content']
                print('Bot:', reply)
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == '__main__':
    chat()
