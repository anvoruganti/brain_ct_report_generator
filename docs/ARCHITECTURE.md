# Architecture Documentation

## System Overview

The Brain CT Report Generator is a FastAPI backend + Streamlit frontend application that fetches Brain CT images from Kheops.online, uses MONAI for abnormality detection, and generates clinical reports using Llama LLM.

## Architecture Diagram

```
┌─────────────────┐
│  Streamlit UI   │
└────────┬────────┘
         │ HTTP Requests
         ▼
┌─────────────────┐
│  FastAPI Backend│
└────────┬────────┘
         │
    ┌────┴────┬──────────┬──────────┐
    ▼         ▼          ▼          ▼
┌────────┐ ┌──────┐ ┌────────┐ ┌────────┐
│ Kheops │ │DICOM │ │ MONAI  │ │  LLM   │
│Service │ │Parser│ │Service │ │Service │
└────────┘ └──────┘ └────────┘ └────────┘
```

## Component Interactions

### 1. Kheops Service
- **Responsibility**: Fetch DICOM data from Kheops.online using album tokens
- **Interface**: `IKheopsClient`
- **Methods**: `fetch_studies()`, `fetch_series()`, `download_instance()`

### 2. DICOM Parser
- **Responsibility**: Parse DICOM files and extract pixel arrays
- **Interface**: `IDicomParser`
- **Methods**: `parse_dicom_file()`, `extract_pixel_array()`, `normalize_image()`

### 3. MONAI Service
- **Responsibility**: Run inference on CT images for abnormality detection
- **Interface**: `IDiagnosisProvider`
- **Methods**: `load_model()`, `preprocess_image()`, `run_inference()`

### 4. LLM Service
- **Responsibility**: Generate clinical reports from diagnosis results
- **Interface**: `IReportGenerator`
- **Methods**: `initialize_llm()`, `create_prompt()`, `generate_report()`, `format_report()`

### 5. Report Generator
- **Responsibility**: Orchestrate the end-to-end workflow
- **Dependencies**: All above services via dependency injection

## Data Flow

1. **User Input**: Album token + Study ID (or DICOM file upload)
2. **Kheops Retrieval**: Fetch DICOM instances from Kheops
3. **DICOM Parsing**: Parse DICOM and extract pixel arrays
4. **Preprocessing**: Normalize images for model input
5. **MONAI Inference**: Detect abnormalities using MONAI model
6. **LLM Generation**: Generate clinical report from diagnosis
7. **Response**: Return formatted report to user

## SOLID Principles Application

### Single Responsibility
- Each service has one clear purpose
- Kheops service only handles API communication
- DICOM parser only handles file parsing
- MONAI service only handles model inference
- LLM service only handles report generation

### Open/Closed
- Services implement interfaces, extensible without modification
- New implementations can be added by implementing interfaces

### Liskov Substitution
- Interface implementations are interchangeable
- Mock services can replace real services in tests

### Interface Segregation
- Small, focused interfaces (`IKheopsClient`, `IDiagnosisProvider`, etc.)
- Clients only depend on methods they use

### Dependency Inversion
- High-level modules depend on abstractions (interfaces)
- Dependencies injected via constructors
- Enables easy testing and mocking

## Technology Stack

- **Backend**: FastAPI, Python 3.9+
- **Frontend**: Streamlit
- **ML Framework**: MONAI, PyTorch
- **LLM**: Ollama (Llama models)
- **DICOM**: pydicom
- **Testing**: pytest, pytest-cov
