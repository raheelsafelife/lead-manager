#!/bin/bash

# Initialize the database
python create_db.py

# Start FastAPI in the foreground on the port provided by Railway
uvicorn api_server:app --host 0.0.0.0 --port $PORT
