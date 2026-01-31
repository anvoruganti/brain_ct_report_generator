# API Reference

## Base URL

```
http://localhost:8000
```

## Endpoints

### Health Check

#### GET `/api/health`

Check API health status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00"
}
```

---

### Kheops Endpoints

#### GET `/api/kheops/studies`

Get all studies from a Kheops album.

**Query Parameters:**
- `album_token` (string, required): Album token for authentication

**Response:**
```json
{
  "studies": [
    {
      "study_id": "1.2.3.4.5",
      "study_date": "20240101",
      "study_description": "Brain CT",
      "patient_id": "PATIENT001",
      "patient_name": "John^Doe"
    }
  ]
}
```

**Error Responses:**
- `500`: Failed to fetch studies

---

#### GET `/api/kheops/studies/{study_id}/series`

Get all series within a study.

**Path Parameters:**
- `study_id` (string, required): Study instance UID

**Query Parameters:**
- `album_token` (string, required): Album token for authentication

**Response:**
```json
{
  "series": [
    {
      "series_id": "1.2.3.4.5.6",
      "study_id": "1.2.3.4.5",
      "series_description": "Axial",
      "modality": "CT",
      "instance_count": 100
    }
  ]
}
```

**Error Responses:**
- `500`: Failed to fetch series

---

### Inference Endpoints

#### POST `/api/inference/from-kheops`

Generate report from Kheops study.

**Request Body:**
```json
{
  "album_token": "your_album_token",
  "study_id": "1.2.3.4.5",
  "series_id": "1.2.3.4.5.6"  // Optional
}
```

**Response:**
```json
{
  "report": {
    "clinical_history": "Patient presents with headache...",
    "findings": "CT scan shows...",
    "impression": "No acute abnormalities...",
    "recommendations": "Follow-up in 3 months...",
    "generated_at": "2024-01-01T12:00:00"
  },
  "diagnosis": {
    "abnormalities": ["normal"],
    "confidence_scores": {
      "normal": 0.9,
      "abnormal": 0.1
    },
    "findings": {
      "max_probability": 0.95
    },
    "timestamp": "2024-01-01T12:00:00"
  },
  "dicom_metadata": {
    "study_id": "1.2.3.4.5",
    "series_id": "1.2.3.4.5.6",
    "patient_id": "PATIENT001",
    "patient_name": "John^Doe"
  }
}
```

**Error Responses:**
- `500`: Failed to generate report

---

#### POST `/api/inference/from-dicom`

Generate report from uploaded DICOM file.

**Request:**
- Content-Type: `multipart/form-data`
- Form field: `dicom_file` (file, required)

**Response:**
Same as `/api/inference/from-kheops`

**Error Responses:**
- `500`: Failed to generate report

---

## Error Handling

All endpoints return standard HTTP status codes:

- `200`: Success
- `400`: Bad Request
- `500`: Internal Server Error

Error response format:
```json
{
  "detail": "Error message description"
}
```

## Authentication

Kheops endpoints require an `album_token` query parameter or in request body. The token provides read access to DICOM data in the specified album.

## Rate Limiting

Currently no rate limiting is implemented. Consider adding rate limiting for production use.

## Examples

### Using cURL

```bash
# Health check
curl http://localhost:8000/api/health

# Get studies
curl "http://localhost:8000/api/kheops/studies?album_token=your_token"

# Generate report
curl -X POST http://localhost:8000/api/inference/from-kheops \
  -H "Content-Type: application/json" \
  -d '{
    "album_token": "your_token",
    "study_id": "1.2.3.4.5"
  }'
```

### Using Python requests

```python
import requests

# Health check
response = requests.get("http://localhost:8000/api/health")
print(response.json())

# Generate report
response = requests.post(
    "http://localhost:8000/api/inference/from-kheops",
    json={
        "album_token": "your_token",
        "study_id": "1.2.3.4.5"
    }
)
print(response.json())
```
