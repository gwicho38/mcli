# Vector Store Manager - Troubleshooting Guide

## Issue: UI Hangs After File Upload

If the UI hangs after uploading files to your vector store, it's likely due to missing Python dependencies. The error message typically shows:

```
ModuleNotFoundError: No module named 'torch'
```

## Quick Fix

1. **Navigate to your Vector Store app directory:**
   ```bash
   cd /path/to/your/vector-store-app
   ```

2. **Run the fix script:**
   ```bash
   ./fix_python_deps.sh
   ```

3. **Test the Python environment:**
   ```bash
   python test_python_env.py
   ```

4. **Restart the app:**
   ```bash
   npm start
   ```

## Manual Fix

If the automatic fix doesn't work, follow these steps:

1. **Create/activate virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install PyTorch:**
   ```bash
   pip install torch==2.1.0 --index-url https://download.pytorch.org/whl/cpu
   ```

3. **Install other dependencies:**
   ```bash
   cd python
   pip install -r requirements_minimal.txt
   cd ..
   ```

4. **Test installation:**
   ```bash
   python test_python_env.py
   ```

## Common Issues

### Issue 1: Permission Denied
```bash
chmod +x fix_python_deps.sh
```

### Issue 2: Python not found
Make sure Python 3.8+ is installed:
```bash
python3 --version
```

### Issue 3: Virtual environment not activated
The app needs to use the virtual environment's Python. Make sure the `venv` directory exists in your app folder.

### Issue 4: Memory issues
If you're on a system with limited RAM (< 8GB), the embedding generation might fail. Try:
- Upload smaller files
- Close other applications
- Use the minimal requirements file

## Verification

After fixing, you should see:
- No error messages when starting the app
- Files upload and process successfully
- Search functionality works
- No hanging UI

## Getting Help

If you're still having issues:
1. Check the console output for specific error messages
2. Run `python test_python_env.py` to verify dependencies
3. Check that the virtual environment is properly set up
4. Ensure you have sufficient disk space and memory 