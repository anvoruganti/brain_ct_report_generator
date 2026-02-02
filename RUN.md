# How to Run the Application

## Quick Start Guide

### Step 1: Set Up Environment Variables

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Edit `.env` and add your Kheops album token:
```bash
KHEOPS_ALBUM_TOKEN=dhUYc3FOZ4hvyXvIAIuucQ
```

### Step 2: Install Dependencies

**Option A: Using Virtual Environment (Recommended)**

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install backend dependencies
cd backend
pip install -r requirements.txt

# Install frontend dependencies
cd ../frontend
pip install -r requirements.txt

# Go back to root
cd ..
```

**Option B: Install Globally**

```bash
# Backend
cd backend
pip install -r requirements.txt

# Frontend
cd ../frontend
pip install -r requirements.txt

cd ..
```

### Step 3: Set Up Ollama (for LLM)

If you haven't installed Ollama:

```bash
# Install Ollama (macOS)
brew install ollama

# Or download from https://ollama.ai
```

Start Ollama and pull the model:

```bash
# Start Ollama service
ollama serve

# In another terminal, pull the model
ollama pull llama3
# or
ollama pull llama2
```

### Step 4: Run the Application

You need **two terminal windows**:

**Terminal 1 - Backend (FastAPI):**
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**Terminal 2 - Frontend (Streamlit):**
```bash
cd frontend
streamlit run streamlit_app.py
```

You should see:
```
You can now view your Streamlit app in your browser.

Local URL: http://localhost:8501
```

### Step 5: Access the Application

- **Streamlit Frontend**: http://localhost:8501
- **FastAPI API Docs**: http://localhost:8000/docs
- **FastAPI ReDoc**: http://localhost:8000/redoc

## Using Docker (Alternative)

If you prefer Docker:

```bash
# Make sure you have .env file configured
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Troubleshooting

### Backend won't start

1. **Port 8000 already in use:**
   ```bash
   # Find process using port 8000
   lsof -i :8000
   # Kill it or change port in .env
   ```

2. **Import errors:**
   ```bash
   # Make sure you're in the backend directory
   cd backend
   # Verify Python path
   python -c "import sys; print(sys.path)"
   ```

3. **Missing dependencies:**
   ```bash
   pip install -r backend/requirements.txt
   ```

### Frontend won't start

1. **Port 8501 already in use:**
   ```bash
   lsof -i :8501
   ```

2. **Backend not running:**
   - Make sure backend is running on port 8000
   - Check `http://localhost:8000/api/health`

### Ollama issues

1. **Ollama not running:**
   ```bash
   ollama serve
   ```

2. **Model not found:**
   ```bash
   ollama pull llama3
   ```

3. **Connection refused:**
   - Check `OLLAMA_BASE_URL` in `.env`
   - Default: `http://localhost:11434`

### Kheops API issues

1. **Invalid token:**
   - Verify your album token in `.env`
   - Token: `dhUYc3FOZ4hvyXvIAIuucQ`

2. **Connection errors:**
   - Check `KHEOPS_BASE_URL` in `.env`
   - Default: `https://demo.kheops.online`

## Testing

Run tests to verify everything works:

```bash
cd backend
pytest --cov=app --cov-report=term-missing
```

## Next Steps

1. Open http://localhost:8501 in your browser
2. Enter your Kheops album token
3. Select a study and series
4. Generate a report!

For more details, see:
- [Development Guide](docs/DEVELOPMENT.md)
- [API Reference](docs/API_REFERENCE.md)
