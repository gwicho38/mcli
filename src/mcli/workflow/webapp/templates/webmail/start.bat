@echo off
REM Vector Store Manager Windows Startup Script

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Set environment variables
set NODE_ENV=production
set PORT=3001

REM Start the application
npm start
pause
