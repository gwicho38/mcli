#!/bin/bash

# Vector Store Manager Development Startup Script

# Activate virtual environment
source venv/bin/activate

# Set environment variables
export NODE_ENV=development
export PORT=3001

# Start the application in development mode
npm run dev
