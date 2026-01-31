# Onboarding Guide

Welcome to the Brain CT Report Generator project! This guide will help you get started quickly.

## Quick Start

1. **Clone and setup** (see [DEVELOPMENT.md](DEVELOPMENT.md))
2. **Run tests** to verify setup: `pytest --cov=app`
3. **Start backend**: `uvicorn app.main:app --reload`
4. **Start frontend**: `streamlit run streamlit_app.py`
5. **Explore API docs**: `http://localhost:8000/docs`

## Project Structure

```
backend/app/
├── api/              # FastAPI routes
├── services/         # Business logic services
│   ├── interfaces.py      # Abstract base classes
│   ├── kheops_service.py  # Kheops API client
│   ├── dicom_parser.py    # DICOM file parsing
│   ├── monai_service.py   # MONAI model inference
│   ├── llm_service.py     # LLM report generation
│   └── report_generator.py # Orchestrator
├── models/          # Data models
│   ├── domain.py    # Domain models
│   └── schemas.py   # API schemas
├── utils/           # Utilities
└── config.py       # Configuration

backend/tests/
├── unit/            # Unit tests
└── integration/    # Integration tests
```

## Key Concepts

### SOLID Principles

1. **Single Responsibility**: Each class/service has one job
2. **Open/Closed**: Extend via interfaces, not modification
3. **Liskov Substitution**: Implementations are interchangeable
4. **Interface Segregation**: Small, focused interfaces
5. **Dependency Inversion**: Depend on abstractions, not concretions

### AAA Testing Format

All tests follow Arrange-Act-Assert pattern:

```python
def test_example():
    # Arrange: Setup test data
    service = MyService()
    input_data = TestData()
    
    # Act: Execute function
    result = service.process(input_data)
    
    # Assert: Verify results
    assert result == expected_output
```

### Dependency Injection

Services receive dependencies via constructor:

```python
class ReportGenerator:
    def __init__(
        self,
        kheops_client: IKheopsClient = None,
        dicom_parser: IDicomParser = None,
        ...
    ):
        self.kheops_client = kheops_client or KheopsService()
```

This enables:
- Easy testing with mocks
- Flexible service swapping
- Loose coupling

## Common Tasks

### Adding a New Service

1. Create interface in `services/interfaces.py`
2. Implement service in `services/your_service.py`
3. Add dependency function in `dependencies.py`
4. Write unit tests in `tests/unit/test_your_service.py`
5. Use in routes via dependency injection

### Adding a New API Endpoint

1. Add route in `api/routes.py`
2. Create request/response schemas in `models/schemas.py`
3. Use dependency injection for services
4. Add integration test in `tests/integration/test_api_routes.py`

### Running Tests

```bash
# All tests
pytest

# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# With coverage
pytest --cov=app --cov-report=html
```

### Code Quality Checks

```bash
# Format code
black .

# Lint code
ruff check .

# Type checking
mypy backend/app
```

## Development Workflow

1. **Create feature branch**: `git checkout -b feature/your-feature`
2. **Implement feature** with tests
3. **Ensure 100% coverage**: `pytest --cov=app`
4. **Commit with conventional format**: `feat: Add your feature`
5. **Create PR** with template
6. **Address review comments**
7. **Merge after approval**

## Getting Help

- Check [ARCHITECTURE.md](ARCHITECTURE.md) for system design
- Check [API_REFERENCE.md](API_REFERENCE.md) for API details
- Check [DEVELOPMENT.md](DEVELOPMENT.md) for setup and guidelines
- Review existing code and tests for examples

## Next Steps

1. Read through the codebase starting with `main.py`
2. Run the application and test the API endpoints
3. Explore the Streamlit frontend
4. Review test files to understand testing patterns
5. Pick a small task to get familiar with the codebase

Happy coding! 🚀
