# Quick Start Guide

## 🚀 Starting the Backend

### ⚠️ IMPORTANT: Run from PROJECT ROOT

You **MUST** run uvicorn from the project root directory, NOT from inside `backend/`:

```bash
# ✅ CORRECT - From project root
cd "/Users/anirudh/Desktop/workspace/CT Brain Image Software/brain_ct_report_generator"
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

# ❌ WRONG - Don't do this
cd backend
uvicorn app.main:app --reload  # This will fail with "No module named 'backend'"
```

### Why?

The imports use `from backend.app.main import app`, which requires Python to find the `backend` module. This only works when running from the project root where `backend/` is a subdirectory.

## 📋 Complete Startup Sequence

### 1. Install Dependencies (First Time Only)

```bash
cd "/Users/anirudh/Desktop/workspace/CT Brain Image Software/brain_ct_report_generator"

# Install backend dependencies
cd backend
pip install -r requirements.txt

# Install pixel decoding libraries (CRITICAL for DICOM)
pip install pylibjpeg pylibjpeg-libjpeg pylibjpeg-openjpeg

# Go back to project root
cd ..
```

### 2. Start Backend

```bash
# Make sure you're in project root
cd "/Users/anirudh/Desktop/workspace/CT Brain Image Software/brain_ct_report_generator"

# Activate venv (if using venv)
source backend/.venv/bin/activate

# Start backend with reload exclusions (prevents watching .venv)
# Option A: From project root (recommended)
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000 --reload-dir backend/app --reload-exclude "**/.venv/*" --reload-exclude "**/site-packages/*"

# Option B: Simple version (if not using venv)
# uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

**Look for this log message:**
```
✅ Using MPS (Metal) backend for M1 Mac acceleration
```

### 3. Start Frontend (Separate Terminal)

```bash
cd "/Users/anirudh/Desktop/workspace/CT Brain Image Software/brain_ct_report_generator/frontend"
streamlit run streamlit_app.py
```

### 4. Access Application

- **Frontend**: http://localhost:8501
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health

## 🔍 Troubleshooting

### Error: "No module named 'backend'"

**Cause**: Running uvicorn from wrong directory

**Fix**: 
```bash
# Make sure you're in project root
cd "/Users/anirudh/Desktop/workspace/CT Brain Image Software/brain_ct_report_generator"
# Then run uvicorn
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

### Error: Port 8000 already in use

**Fix**:
```bash
# Find and kill process using port 8000
lsof -ti:8000 | xargs kill -9

# Or use different port
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8001
```

### Error: Pixel decoding fails

**Fix**: Install pixel decoding libraries:
```bash
pip install pylibjpeg pylibjpeg-libjpeg pylibjpeg-openjpeg
```

See `SETUP_PIXEL_DECODING.md` for details.

## ✅ Verification Checklist

- [ ] Backend starts without errors
- [ ] See "✅ Using MPS (Metal) backend" in logs
- [ ] Health check works: `curl http://localhost:8000/api/health`
- [ ] Frontend connects to backend (green checkmark in sidebar)
- [ ] Can upload DICOM files successfully

## 📝 Quick Reference

| Component | Command | Port |
|-----------|---------|------|
| Backend | `uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000` | 8000 |
| Frontend | `streamlit run streamlit_app.py` | 8501 |

**Remember**: Always run backend command from **project root**, not from `backend/` directory!
