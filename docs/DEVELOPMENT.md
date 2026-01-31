# Development Guide

## Local Setup

### Prerequisites

- Python 3.9 or higher
- pip or conda
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd brain_ct_report_generator
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install backend dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

4. **Install frontend dependencies**
   ```bash
   cd ../frontend
   pip install -r requirements.txt
   ```

5. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

### Running the Application

1. **Start FastAPI backend**
   ```bash
   cd backend
   uvicorn app.main:app --reload
   ```
   Backend will be available at `http://localhost:8000`

2. **Start Streamlit frontend** (in a new terminal)
   ```bash
   cd frontend
   streamlit run streamlit_app.py
   ```
   Frontend will be available at `http://localhost:8501`

3. **Access API documentation**
   - Swagger UI: `http://localhost:8000/docs`
   - ReDoc: `http://localhost:8000/redoc`

## Running Tests

### Unit Tests

```bash
cd backend
pytest tests/unit/ -v
```

### Integration Tests

```bash
cd backend
pytest tests/integration/ -v
```

### All Tests with Coverage

```bash
cd backend
pytest --cov=app --cov-report=html --cov-report=term-missing
```

Coverage report will be generated in `htmlcov/index.html`

## Code Style Guidelines

### Python Style

- Follow PEP 8
- Use type hints for all functions
- Maximum line length: 100 characters
- Use black for formatting: `black .`
- Use ruff for linting: `ruff check .`

### Function Guidelines

- Keep functions small (< 15 lines when possible)
- Single responsibility per function
- Use descriptive names
- Add docstrings for all functions

### Testing Guidelines

- Use AAA format (Arrange, Act, Assert)
- One assertion per test when possible
- Mock external dependencies
- Aim for 100% code coverage

### Commit Guidelines

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` - New feature
- `fix:` - Bug fix
- `test:` - Adding or updating tests
- `docs:` - Documentation changes
- `refactor:` - Code refactoring
- `chore:` - Build/tooling changes

Example:
```
feat: Add Kheops service with DICOM retrieval

- Implement KheopsService class
- Add fetch_studies, fetch_series, download_instance methods
- Include unit tests with 100% coverage
```

## Git Workflow

1. Create feature branch: `git checkout -b feature/feature-name`
2. Make changes and commit with meaningful messages
3. Write tests and ensure 100% coverage
4. Push branch: `git push origin feature/feature-name`
5. Create Pull Request with template
6. Address review comments
7. Merge after approval

## Project Structure

```
brain_ct_report_generator/
├── backend/
│   ├── app/              # Application code
│   │   ├── api/         # API routes
│   │   ├── services/    # Business logic
│   │   ├── models/     # Data models
│   │   └── utils/      # Utilities
│   └── tests/          # Test files
├── frontend/            # Streamlit frontend
└── docs/               # Documentation
```

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure you're in the correct directory and virtual environment is activated
2. **Port already in use**: Change ports in `.env` or kill existing processes
3. **Ollama not running**: Start Ollama service: `ollama serve`
4. **Model not found**: Ensure MONAI model is downloaded and path is correct in `.env`
