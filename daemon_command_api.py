

from flask import Flask, request, jsonify
import subprocess

import threading
import time
import glob
import os
try:
    import tomllib
    _use_tomllib = True
except ImportError:
    import toml
    _use_tomllib = False


app = Flask(__name__)

# Example internal app state
app_state = {
    'users': ['alice', 'bob', 'carol'],
    'status': 'running',
    'uptime': 0
}

# Background thread to update uptime
def update_uptime():
    while True:
        app_state['uptime'] += 1
        time.sleep(1)

threading.Thread(target=update_uptime, daemon=True).start()



# OpenAI-compatible endpoints
@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    data = request.get_json()
    messages = data.get('messages', [])
    # Simple echo bot for demo
    if messages:
        last_message = messages[-1]['content']
        response = f"Echo: {last_message}"
    else:
        response = "Hello!"
    return jsonify({
        'id': 'chatcmpl-demo',
        'object': 'chat.completion',
        'created': int(time.time()),
        'model': 'mcli-echo-001',
        'choices': [{
            'index': 0,
            'message': {'role': 'assistant', 'content': response},
            'finish_reason': 'stop'
        }],
        'usage': {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
    })

@app.route('/v1/completions', methods=['POST'])
def completions():
    data = request.get_json()
    prompt = data.get('prompt', '')
    return jsonify({
        'id': 'cmpl-demo',
        'object': 'text_completion',
        'created': int(time.time()),
        'model': 'mcli-echo-001',
        'choices': [{
            'text': f'Echo: {prompt}',
            'index': 0,
            'logprobs': None,
            'finish_reason': 'stop'
        }],
        'usage': {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
    })

@app.route('/v1/models', methods=['GET'])
def models():
    return jsonify({
        'object': 'list',
        'data': [
            {'id': 'mcli-echo-001', 'object': 'model', 'owned_by': 'user', 'permission': []}
        ]
    })

@app.route('/v1/embeddings', methods=['POST'])
def embeddings():
    data = request.get_json()
    input_text = data.get('input', '')
    # Return a fake embedding
    return jsonify({
        'object': 'list',
        'data': [{
            'object': 'embedding',
            'embedding': [0.0] * 10,
            'index': 0
        }],
        'model': 'mcli-echo-001',
        'usage': {'prompt_tokens': 0, 'total_tokens': 0}
    })

@app.route('/v1/files', methods=['GET', 'POST'])
def files():
    return jsonify({'object': 'list', 'data': []})

@app.route('/v1/images/generations', methods=['POST'])
def images_generations():
    return jsonify({'data': [], 'created': int(time.time())})

@app.route('/v1/audio/transcriptions', methods=['POST'])
def audio_transcriptions():
    return jsonify({'text': '', 'language': 'en'})

@app.route('/v1/audio/translations', methods=['POST'])
def audio_translations():
    return jsonify({'text': '', 'language': 'en'})

@app.route('/v1/moderations', methods=['POST'])
def moderations():
    return jsonify({'results': [{'flagged': False, 'categories': {}}]})

# Internal app state search endpoint
@app.route('/search_state', methods=['POST'])
def search_state():
    data = request.get_json()
    query = data.get('query', '').lower()
    # Simple search: return keys/values containing the query
    results = {}
    for k, v in app_state.items():
        if query in k.lower() or (isinstance(v, str) and query in v.lower()) or (isinstance(v, list) and any(query in str(item).lower() for item in v)):
            results[k] = v
    return jsonify({'results': results})

# Command execution endpoint (unchanged, but now can use app_state if needed)
@app.route('/execute', methods=['POST'])
def execute_command():
    data = request.get_json()
    command = data.get('command')
    if not command:
        return jsonify({'error': 'No command provided'}), 400
    try:
        # For security, you may want to restrict allowed commands here
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return jsonify({
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500



# User command management endpoints

import importlib.util
import inspect
from pathlib import Path

def get_included_dirs():
    # Find config.toml in the same way as CLI
    config_paths = [
        Path("config.toml"),
        Path(__file__).parent / "config.toml",
        Path(__file__).parent.parent.parent / "config.toml"
    ]
    for file in config_paths:
        if file.exists():
            if _use_tomllib:
                with open(file, 'rb') as f:
                    data = tomllib.load(f)
            else:
                with open(file, 'r', encoding='utf-8') as f:
                    data = toml.load(f)
            return data.get('paths', {}).get('included_dirs', [])
    return []

def discover_python_commands():
    included_dirs = get_included_dirs()
    print(f"[DEBUG] Included dirs: {included_dirs}")
    base_path = Path(__file__).parent.parent
    commands = set()
    for directory in included_dirs:
        search_path = base_path / directory
        if not search_path.exists():
            continue
        for py_file in search_path.rglob('*.py'):
            module_name = None
            try:
                rel_path = py_file.relative_to(base_path.parent)
                module_name = str(rel_path).replace('/', '.').replace('\\', '.').replace('.py', '')
                spec = importlib.util.spec_from_file_location(module_name, py_file)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    for name, obj in inspect.getmembers(mod):
                        # Detect Click commands
                        if hasattr(obj, '__module__') and obj.__module__ == module_name:
                            if hasattr(obj, 'name') and callable(obj):
                                commands.add(obj.name)
            except Exception as e:
                print(f"[DEBUG] Error inspecting {py_file}: {e}")
                continue
    print(f"[DEBUG] Discovered python commands: {commands}")
    return list(commands)

user_commands = {}
user_commands = {}

@app.route('/commands', methods=['GET'])
def list_commands():
    # Discover python commands dynamically
    discovered = set(discover_python_commands())
    all_commands = set(user_commands.keys()) | discovered
    return jsonify({'commands': sorted(all_commands)})

@app.route('/commands', methods=['POST'])
def add_command():
    data = request.get_json()
    name = data.get('name')
    command = data.get('command')
    if not name or not command:
        return jsonify({'error': 'Name and command required'}), 400
    user_commands[name] = command
    return jsonify({'message': f'Command {name} added.'})

@app.route('/commands/<name>', methods=['PUT'])
def modify_command(name):
    data = request.get_json()
    command = data.get('command')
    # Allow modifying only user-added commands
    if name not in user_commands:
        return jsonify({'error': 'Command not found or not user-modifiable'}), 404
    user_commands[name] = command
    return jsonify({'message': f'Command {name} modified.'})

@app.route('/commands/<name>/execute', methods=['POST'])
def execute_user_command(name):
    # Merge config and user commands, user commands override config if same name
    all_commands = dict(config_commands)
    all_commands.update(user_commands)
    if name not in all_commands:
        return jsonify({'error': 'Command not found'}), 404
    try:
        result = subprocess.run(all_commands[name], shell=True, capture_output=True, text=True)
        return jsonify({
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5005)
