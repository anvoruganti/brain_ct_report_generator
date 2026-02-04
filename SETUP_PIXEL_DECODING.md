# DICOM Pixel Decoding Setup Guide

## 🔴 Critical Issue: Compressed DICOM Pixel Data

Your KHEOPS DICOM files use **compressed pixel data** (JPEG/JPEG-LS/JPEG2000). 
`pydicom` alone cannot decode these - you need additional pixel decoding libraries.

## ✅ Quick Fix (Recommended)

### Step 1: Install Pixel Decoding Libraries

```bash
cd "/Users/anirudh/Desktop/workspace/CT Brain Image Software/brain_ct_report_generator/backend"
pip install pylibjpeg pylibjpeg-libjpeg pylibjpeg-openjpeg
```

**OR** (alternative):

```bash
pip install gdcm
```

### Step 2: Verify Installation

```bash
python3 -c "import pylibjpeg; print('✅ pylibjpeg installed')"
python3 -c "import pydicom; print('✅ pydicom can now decode compressed DICOM')"
```

### Step 3: Restart Backend

The backend will automatically use these libraries when decoding pixel data.

## 🐍 Python Version Issue (If Still Having Problems)

If you're using **Python 3.13**, you may encounter compatibility issues:

### Option A: Use Python 3.11 (Recommended for Medical Imaging)

```bash
# Create new conda environment
conda create -n ctmonai python=3.11 -y
conda activate ctmonai

# Install all dependencies
cd "/Users/anirudh/Desktop/workspace/CT Brain Image Software/brain_ct_report_generator/backend"
pip install -r requirements.txt

# Install pixel decoders
pip install pylibjpeg pylibjpeg-libjpeg pylibjpeg-openjpeg
```

### Option B: Stay on Python 3.13 (May Have Issues)

If you must use Python 3.13:
- Some packages may not be available
- You may need to build from source
- Not recommended for production medical imaging

## 🔍 How to Verify It's Working

### Test with Your DICOM Files

1. **Start backend**:
   ```bash
   uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Upload DICOM files** via Streamlit UI

3. **Check backend logs** - you should see:
   - ✅ Files parsing successfully
   - ✅ Pixel arrays extracted
   - ✅ No "compressed" or "decompress" errors

### If You Still See Errors

The improved error messages will now show:
- **Transfer Syntax** (compression type)
- **Exact error** with full traceback
- **Installation instructions** for missing libraries

Example error message:
```
⚠️ PIXEL DECODING ERROR - Compressed DICOM detected!
Transfer Syntax: 1.2.840.10008.1.2.4.70
This DICOM uses compressed pixel data (JPEG/JPEG-LS/JPEG2000).
Install pixel decoding libraries:
  pip install pylibjpeg pylibjpeg-libjpeg pylibjpeg-openjpeg
```

## 📋 What Was Fixed

1. ✅ **Added pixel decoding libraries** to `requirements.txt`
2. ✅ **Improved error messages** - now shows transfer syntax and compression type
3. ✅ **Better exception handling** - full tracebacks logged
4. ✅ **Helpful error messages** - tells you exactly what to install

## 🎯 Expected Behavior After Fix

- **Before**: All files fail with "None" error
- **After**: Files decode successfully, pixel arrays extracted

## 📚 Technical Details

### Why This Happens

CT scans from PACS systems (like KHEOPS) are often stored with:
- **JPEG compression** (lossy, smaller files)
- **JPEG-LS compression** (lossless, medical-grade)
- **JPEG2000 compression** (high quality, DICOM standard)

`pydicom` can read the DICOM headers but needs plugins to decode compressed pixels.

### Libraries Explained

- **pylibjpeg**: Python wrapper for JPEG decoding
- **pylibjpeg-libjpeg**: JPEG decoder backend
- **pylibjpeg-openjpeg**: JPEG2000 decoder backend
- **gdcm**: Alternative (all-in-one DICOM toolkit)

Both approaches work - choose based on what installs cleanly on your system.
