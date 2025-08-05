def test_search_state():
    print('Testing /search_state...')
    payload = {'query': 'user'}
    r = requests.post(f'{BASE_URL}/search_state', json=payload)
    print('Response:', r.json())

def test_execute():
    print('Testing /execute...')
    payload = {'command': 'echo hello from mcli'}
    r = requests.post(f'{BASE_URL}/execute', json=payload)
    print('Response:', r.json())
import requests

BASE_URL = 'http://127.0.0.1:5005'

def test_chat_completions():
    print('Testing /v1/chat/completions...')
    payload = {
        'messages': [
            {'role': 'user', 'content': 'Hello, who are you?'}
        ]
    }
    r = requests.post(f'{BASE_URL}/v1/chat/completions', json=payload)
    print('Response:', r.json())
def test_completions():
    print('Testing /v1/completions...')
    payload = {'prompt': 'Say hello'}
    r = requests.post(f'{BASE_URL}/v1/completions', json=payload)
    print('Response:', r.json())

def test_models():
    print('Testing /v1/models...')
    r = requests.get(f'{BASE_URL}/v1/models')
    print('Response:', r.json())

def test_embeddings():
    print('Testing /v1/embeddings...')
    payload = {'input': 'test'}
    r = requests.post(f'{BASE_URL}/v1/embeddings', json=payload)
    print('Response:', r.json())

def test_files():
    print('Testing /v1/files...')
    r = requests.get(f'{BASE_URL}/v1/files')
    print('Response:', r.json())
    r = requests.post(f'{BASE_URL}/v1/files', json={})
    print('POST Response:', r.json())

def test_images_generations():
    print('Testing /v1/images/generations...')
    r = requests.post(f'{BASE_URL}/v1/images/generations', json={})
    print('Response:', r.json())

def test_audio_transcriptions():
    print('Testing /v1/audio/transcriptions...')
    r = requests.post(f'{BASE_URL}/v1/audio/transcriptions', json={})
    print('Response:', r.json())

def test_audio_translations():
    print('Testing /v1/audio/translations...')
    r = requests.post(f'{BASE_URL}/v1/audio/translations', json={})
    print('Response:', r.json())

def test_moderations():
    print('Testing /v1/moderations...')
    r = requests.post(f'{BASE_URL}/v1/moderations', json={})
    print('Response:', r.json())

def main():
    test_chat_completions()
    test_completions()
    test_models()
    test_embeddings()
    test_files()
    test_images_generations()
    test_audio_transcriptions()
    test_audio_translations()
    test_moderations()
    test_search_state()
    test_execute()

if __name__ == '__main__':
    main()
