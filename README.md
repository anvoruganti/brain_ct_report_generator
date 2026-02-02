# Brain CT Report Generator

A FastAPI backend + Streamlit frontend application that generates clinical reports from Brain CT images using MONAI for abnormality detection and Llama LLM for report generation.

## 🎯 Current Status: PoC Version

**This PoC version focuses on local DICOM file upload:**
- ✅ Upload DICOM files directly from your computer
- ✅ Generate reports without external dependencies
- ✅ Simple, fast workflow for testing and validation

**Future MVP Plans:**
- 🔄 AWS HealthImaging integration
- 🔄 Cloud-based DICOM storage
- 🔄 Scalable architecture redesign

## Features

- **Local DICOM Upload**: Upload DICOM files directly from your computer (PoC)
- **MONAI Inference**: Detect abnormalities in Brain CT scans using MONAI models
- **LLM Report Generation**: Generate structured clinical reports using Ollama/Llama
- **Streamlit UI**: User-friendly interface for file upload and report viewing
- **RESTful API**: FastAPI backend with comprehensive endpoints
- **100% Test Coverage**: Comprehensive unit and integration tests
- **SOLID Principles**: Clean architecture with dependency injection
- **Kheops Integration**: Available but disabled for PoC (will be replaced with AWS HealthImaging for MVP)

## Architecture

- **Backend**: FastAPI with service-oriented architecture
- **Frontend**: Streamlit web application
- **ML Framework**: MONAI for medical imaging
- **LLM**: Ollama with Llama models
- **DICOM Processing**: pydicom for DICOM file handling

## Quick Start

### Prerequisites

- Python 3.9+
- Ollama installed and running (for LLM)
- DICOM files for testing (PoC version uses local file upload)

### Installation

1. Clone the repository
   ```bash
   git clone <repository-url>
   cd brain_ct_report_generator
   ```

2. Set up environment
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. Install dependencies
   ```bash
   # Backend
   cd backend
   pip install -r requirements.txt
   
   # Frontend
   cd ../frontend
   pip install -r requirements.txt
   ```

4. Run the application
   ```bash
   # Terminal 1: Backend
   cd backend
   uvicorn app.main:app --reload
   
   # Terminal 2: Frontend
   cd frontend
   streamlit run streamlit_app.py
   ```

5. Access the application
   - Frontend: http://localhost:8501
   - API Docs: http://localhost:8000/docs

### Using the Application (PoC)

1. Start the backend and frontend (see above)
2. Open the Streamlit UI at http://localhost:8501
3. Click "Choose a DICOM file" and select a Brain CT DICOM file from your computer
4. Click "Generate Report"
5. View the generated clinical report with diagnosis and recommendations

## Docker Deployment

```bash
docker-compose up -d
```

## Testing

```bash
cd backend
pytest --cov=app --cov-report=html
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) - System design and SOLID principles
- [Development Guide](docs/DEVELOPMENT.md) - Setup and development guidelines
- [API Reference](docs/API_REFERENCE.md) - API endpoint documentation
- [Onboarding Guide](docs/ONBOARDING.md) - New engineer onboarding

## Project Structure

```
brain_ct_report_generator/
├── backend/          # FastAPI backend
│   ├── app/         # Application code
│   └── tests/       # Test files
├── frontend/        # Streamlit frontend
├── docs/            # Documentation
└── docker-compose.yml
```

## Contributing

1. Create feature branch: `git checkout -b feature/feature-name`
2. Make changes with tests (100% coverage required)
3. Commit with conventional commits format
4. Create Pull Request

## License

MIT
