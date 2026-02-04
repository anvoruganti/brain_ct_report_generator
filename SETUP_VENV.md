# Virtual Environment Setup Guide

## 🎯 Goal: Run Backend on Python 3.11 (Not 3.13)

Python 3.13 has compatibility issues with PyTorch, MONAI, and pixel decoding libraries.
Use Python 3.11 for stable operation.

## ✅ Step-by-Step Setup

### 1. Create Virtual Environment

```bash
cd "/Users/anirudh/Desktop/workspace/CT Brain Image Software/brain_ct_report_generator/backend"

# Create venv with Python 3.10 or 3.11
# Option A: Use Python 3.10 (if available)
python3.10 -m venv .venv

# Option B: Use Python 3.11 (if installed)
# python3.11 -m venv .venv

# Option C: Install Python 3.11 via conda first
# conda install python=3.11 -y
# python3.11 -m venv .venv

# Activate venv
source .venv/bin/activate

# Verify Python version
python --version
# Should show: Python 3.10.x or 3.11.x (NOT 3.13)

# Verify you're using venv Python
which python
# Should show: .../backend/.venv/bin/python
```

### 2. Install Dependencies

```bash
# Make sure venv is activated (you should see (.venv) in prompt)
pip install --upgrade pip

# Install all requirements
pip install -r requirements.txt

# Install pixel decoding libraries (CRITICAL!)
pip install pylibjpeg pylibjpeg-libjpeg pylibjpeg-openjpeg

# Verify installations
python -c "import torch; print('✅ PyTorch:', torch.__version__)"
python -c "import monai; print('✅ MONAI:', monai.__version__)"
python -c "import pydicom; print('✅ pydicom:', pydicom.__version__)"
python -c "import pylibjpeg; print('✅ pylibjpeg installed')"
```

### 3. Verify Uvicorn Installation

```bash
# Check uvicorn location (should be in venv)
which uvicorn
# Should show: .../backend/.venv/bin/uvicorn

# If not found, install explicitly
pip install uvicorn[standard]
```

### 4. Start Backend from Project Root

**IMPORTANT**: Always run from **project root**, not from `backend/`:

```bash
# Go to project root
cd "/Users/anirudh/Desktop/workspace/CT Brain Image Software/brain_ct_report_generator"

# Make sure venv is still activated
source backend/.venv/bin/activate

# Start backend
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

**OR** use Python module syntax (more reliable):

```bash
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Verify Backend Started Correctly

Look for these log messages:

```
BACKEND_PYTHON_VERSION: 3.11.x
✅ Python 3.11 is supported
✅ Using MPS (Metal) backend for M1 Mac acceleration  # (if MPS available)
```

**If you see Python 3.13 warning**, the venv is not active. Reactivate it.

## 🔄 Daily Usage

### Activate Venv and Start Backend

```bash
# Navigate to project root
cd "/Users/anirudh/Desktop/workspace/CT Brain Image Software/brain_ct_report_generator"

# Activate venv
source backend/.venv/bin/activate

# Verify Python version
python --version  # Should be 3.10.x or 3.11.x (NOT 3.13)

# Start backend
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

### Deactivate Venv

```bash
deactivate
```

## 🧪 Test DICOM Decoding

Use the new debug endpoint to test DICOM files:

```bash
# Test with a single DICOM file
curl -X POST "http://localhost:8000/api/debug/dicom" \
  -F "files=@DICOM data /DICOM (1)/DICOM/0/1" \
  | python3 -m json.tool
```

This will show:
- Transfer syntax (compression type)
- Whether pixel data exists
- Whether pixel decoding works
- Detailed error if decoding fails

## ✅ Success Criteria

- [ ] Python version shows 3.11.x (not 3.13)
- [ ] Backend starts without errors
- [ ] See "✅ Python 3.11 is supported" in logs
- [ ] Debug endpoint works: `curl http://localhost:8000/api/debug/dicom`
- [ ] Can upload DICOM files and get reports

## 🐛 Troubleshooting

### "No module named 'backend'"

**Cause**: Running from wrong directory or venv not activated

**Fix**:
```bash
# Make sure you're in project root
cd "/Users/anirudh/Desktop/workspace/CT Brain Image Software/brain_ct_report_generator"

# Activate venv
source backend/.venv/bin/activate

# Use python -m syntax
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

### Still seeing Python 3.13

**Fix**:
```bash
# Deactivate current venv
deactivate

# Remove old venv
rm -rf backend/.venv

# Create new venv with Python 3.10 (or 3.11 if installed)
cd backend
python3.10 -m venv .venv  # Use 3.10 if available
# OR: python3.11 -m venv .venv  # If 3.11 is installed
source .venv/bin/activate

# Verify version
python --version  # Must be 3.10.x or 3.11.x (NOT 3.13)

# Install dependencies
pip install -r requirements.txt
pip install pylibjpeg pylibjpeg-libjpeg pylibjpeg-openjpeg
```

### Pixel decoding still fails

**Check**:
```bash
# Verify libraries installed
python -c "import pylibjpeg; print('OK')"

# Test with debug endpoint
curl -X POST "http://localhost:8000/api/debug/dicom" \
  -F "files=@DICOM data /DICOM (1)/DICOM/0/1"
```

If `pixel_test.ok` is `false`, check the error message - it will tell you what's missing.
