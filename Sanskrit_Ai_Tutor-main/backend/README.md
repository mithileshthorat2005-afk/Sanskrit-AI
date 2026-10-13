# SanskritAI Backend

FastAPI backend for Sanskrit language learning.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the server:
   ```bash
   python main.py
   ```
   Or using uvicorn:
   ```bash
   uvicorn main:app --reload
   ```
   The default port is `8005`; override it by setting the `PORT` environment
   variable before starting the server.

## API Documentation

Once the server is running, visit:
- Swagger UI: [http://localhost:8005/docs](http://localhost:8005/docs)
- Redoc: [http://localhost:8005/redoc](http://localhost:8005/redoc)
