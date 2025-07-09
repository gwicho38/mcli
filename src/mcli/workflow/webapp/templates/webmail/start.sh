#!/bin/bash

# Vector Store Manager Startup Script

# Activate virtual environment
source venv/bin/activate

# Set environment variables
export NODE_ENV=production
export PORT=3001

# Start the application
npm start
