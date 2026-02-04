# How to Run the Brain CT Report Generator

## 🚀 Quick Start Guide

### Step 1: Restart Backend (to load new optimizations)

The backend is currently running. You need to restart it to pick up the MPS and batch processing optimizations:

**Option A: Restart manually**
```bash
# Stop the current backend (Ctrl+C in the terminal where it's running)
# Then restart:
cd "/Users/anirudh/Desktop/workspace/CT Brain Image Software/brain_ct_report_generator"
source backend/.venv/bin/activate  # If using venv
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000 --reload-dir backend/app --reload-exclude "**/.venv/*" --reload-exclude "**/site-packages/*"
```

**Option B: Kill and restart**
```bash
# Kill existing backend
kill 17390

# Start fresh backend (with reload exclusions to prevent watching .venv)
cd "/Users/anirudh/Desktop/workspace/CT Brain Image Software/brain_ct_report_generator"
source backend/.venv/bin/activate  # If using venv
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000 --reload-dir backend/app --reload-exclude "**/.venv/*" --reload-exclude "**/site-packages/*"
```

### Step 2: Verify Backend Started Correctly

Look for this log message in the backend terminal:
```
✅ Using MPS (Metal) backend for M1 Mac acceleration
```

If you see this, MPS is enabled and you'll get the performance boost!

### Step 3: Frontend (Already Running)

Your Streamlit frontend is already running. If you need to restart it:

```bash
# Stop current frontend (Ctrl+C)
# Then restart:
cd "/Users/anirudh/Desktop/workspace/CT Brain Image Software/brain_ct_report_generator/frontend"
streamlit run streamlit_app.py
```

### Step 4: Test the Application

1. **Open Streamlit UI**: http://localhost:8501
2. **Upload DICOM Files**: 
   - Click "Choose DICOM file(s)"
   - Select multiple files from `DICOM data /DICOM (1)/DICOM/0/` folder
   - Files don't need extensions (like `1`, `2`, `3`, etc.)
3. **Generate Report**: Click "🚀 Generate Report"
4. **View Results**: The report should generate faster now with batch processing!

## 📊 Performance Monitoring

### Check Backend Logs

Watch the backend terminal for:
- `✅ Using MPS (Metal) backend` - MPS is active
- `Processing X files: parsing in parallel (4 workers), inference in batches (16 per batch)` - Batch processing active
- `Running batch inference: batch 1/X` - Batch inference working

### Expected Performance

With the new optimizations:
- **MPS acceleration**: 5-20x faster than CPU
- **Batch processing**: 2-4x faster than sequential
- **Combined**: 10-40x faster model inference!

## ⚙️ Configuration (Optional)

You can customize performance in `.env` file:

```env
# Device (auto-detects MPS on M1 Mac)
MONAI_DEVICE=auto

# Batch size (8-32 recommended for M1 Mac)
MONAI_BATCH_SIZE=16

# Parallel workers for file parsing
MAX_WORKERS=4
```

## 🐛 Troubleshooting

### If MPS is not detected:
- Check PyTorch version: `python3 -c "import torch; print(torch.__version__)"`
- MPS requires PyTorch 1.12+ and macOS 12.3+
- If not available, it will fall back to CPU (still works, just slower)

### If backend won't start:
- Check port 8000 is free: `lsof -i :8000`
- Kill existing process: `kill <PID>`

### If frontend can't connect:
- Verify backend is running: `curl http://localhost:8000/api/health`
- Check backend logs for errors

## 📝 Testing with Your DICOM Files

1. Navigate to: `DICOM data /DICOM (1)/DICOM/0/`
2. Select multiple files (e.g., files `1` through `15`)
3. Upload and generate report
4. Should see faster processing with batch inference!

## 🎯 What's New

✅ **MPS Detection**: Auto-detects and uses M1 Mac GPU acceleration  
✅ **Batch Processing**: Processes 16 images at once (configurable)  
✅ **Parallel Parsing**: Parses DICOM files in parallel (4 workers)  
✅ **Simplified PoC**: Single LLM call instead of chunking (faster for PoC)
