import requests

BASE_URL = 'http://127.0.0.1:5005'

def test_add_command():
    print('Adding command...')
    payload = {'name': 'greet', 'command': 'echo Greetings!'}
    r = requests.post(f'{BASE_URL}/commands', json=payload)
    print('Add:', r.json())

def test_modify_command():
    print('Modifying command...')
    payload = {'command': 'echo Hello, modified!'}
    r = requests.put(f'{BASE_URL}/commands/greet', json=payload)
    print('Modify:', r.json())

def test_list_commands():
    print('Listing commands...')
    r = requests.get(f'{BASE_URL}/commands')
    print('List:', r.json())

def test_execute_command():
    print('Executing command...')
    r = requests.post(f'{BASE_URL}/commands/greet/execute')
    print('Execute:', r.json())

def main():
    test_add_command()
    test_modify_command()
    test_list_commands()
    test_execute_command()

if __name__ == '__main__':
    main()
