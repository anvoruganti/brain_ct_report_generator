#!/bin/bash
# Quick setup script for Python 3.10 venv

set -e

echo "=== Brain CT Report Generator - Quick Setup ==="
echo ""

# Check if we're in the right directory
if [ ! -d "backend" ]; then
    echo "❌ Error: Must run from project root directory"
    echo "Current directory: $(pwd)"
    exit 1
fi

# Check Python 3.10 availability
if command -v python3.10 &> /dev/null; then
    PYTHON_CMD="python3.10"
    echo "✅ Found Python 3.10"
elif command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
    echo "✅ Found Python 3.11"
else
    echo "❌ Error: Neither python3.10 nor python3.11 found"
    echo ""
    echo "Install Python 3.10 or 3.11:"
    echo "  Option 1: Install via conda:"
    echo "    conda install python=3.10 -y"
    echo "  Option 2: Install via Homebrew:"
    echo "    brew install python@3.10"
    exit 1
fi

echo "Using: $PYTHON_CMD"
$PYTHON_CMD --version
echo ""

# Create venv
echo "Creating virtual environment..."
cd backend
$PYTHON_CMD -m venv .venv

# Activate venv
echo "Activating virtual environment..."
source .venv/bin/activate

# Verify Python version
PYTHON_VERSION=$(python --version 2>&1)
echo "Virtual environment Python: $PYTHON_VERSION"

if [[ "$PYTHON_VERSION" == *"3.13"* ]]; then
    echo "❌ Warning: Python 3.13 detected in venv!"
    echo "This may cause compatibility issues."
    echo "Please use Python 3.10 or 3.11."
    exit 1
fi

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo ""
echo "Installing requirements..."
pip install -r requirements.txt

# Install pixel decoding libraries
echo ""
echo "Installing pixel decoding libraries..."
pip install pylibjpeg pylibjpeg-libjpeg pylibjpeg-openjpeg

# Verify installations
echo ""
echo "Verifying installations..."
python -c "import torch; print('✅ PyTorch:', torch.__version__)" || echo "❌ PyTorch not installed"
python -c "import monai; print('✅ MONAI:', monai.__version__)" || echo "❌ MONAI not installed"
python -c "import pydicom; print('✅ pydicom:', pydicom.__version__)" || echo "❌ pydicom not installed"
python -c "import pylibjpeg; print('✅ pylibjpeg installed')" || echo "❌ pylibjpeg not installed"

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the backend:"
echo "  1. Activate venv: source backend/.venv/bin/activate"
echo "  2. Go to project root: cd .."
echo "  3. Start backend: python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
