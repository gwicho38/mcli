#!/bin/bash
# Start the FastAPI daemon server with uvicorn
uvicorn mcli.workflow.daemon.daemon_api:app --host 0.0.0.0 --port 5005 --reload
