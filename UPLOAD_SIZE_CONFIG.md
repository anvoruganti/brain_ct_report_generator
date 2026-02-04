# Upload Size Configuration

## Maximum Upload Size: 500 MB

The backend is configured to accept file uploads up to **500 MB**. This allows uploading:
- Large ZIP archives from KHEOPS exports
- Multiple DICOM files in a single upload
- Complete CT scan series

## Configuration

### Backend (FastAPI)

The maximum upload size is configured in `backend/app/config.py`:

```python
max_upload_size_mb: int = Field(
    default=500,
    description="Maximum file upload size in MB (for ZIP files and DICOM series)",
)
```

You can override this in your `.env` file:

```env
MAX_UPLOAD_SIZE_MB=500
```

### Starting Backend with Large Upload Support

When starting uvicorn, ensure it can handle large requests. The default uvicorn configuration should work, but if you encounter issues, you can explicitly set limits:

```bash
# Standard command (should work for 500MB)
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

# If you need to increase limits explicitly (usually not needed)
python -m uvicorn backend.app.main:app \
  --reload \
  --host 0.0.0.0 \
  --port 8000 \
  --limit-concurrency 1000 \
  --timeout-keep-alive 300
```

### Frontend (Streamlit)

**Note**: Streamlit has a default upload limit of **200 MB per file**. For ZIP files larger than 200 MB:

**Option 1**: Configure Streamlit server (recommended)

Create or update `~/.streamlit/config.toml`:

```toml
[server]
maxUploadSize = 500
```

Then restart Streamlit.

**Option 2**: Use API directly

For files larger than Streamlit's limit, use the API directly:

```bash
curl -X POST "http://localhost:8000/api/inference/from-dicom" \
  -F "dicom_files=@large_file.zip" \
  -H "Content-Type: multipart/form-data"
```

## Testing Upload Size

### Check Current Limits

```bash
# Test with a file
curl -X POST "http://localhost:8000/api/inference/from-dicom" \
  -F "dicom_files=@test.zip" \
  -v
```

### Error Messages

If a file exceeds the limit, you'll see:

```
413 Request Entity Too Large
{
  "detail": "File too large. Maximum upload size is 500 MB. Received 600.00 MB."
}
```

## Increasing Upload Size (If Needed)

To increase beyond 500 MB:

1. **Update `.env`**:
   ```env
   MAX_UPLOAD_SIZE_MB=1000  # 1 GB
   ```

2. **Restart backend** to apply changes

3. **Update Streamlit config** if using frontend:
   ```toml
   [server]
   maxUploadSize = 1000
   ```

## Performance Considerations

- **Large ZIP files** may take time to extract and process
- **Memory usage** increases with file size
- **Processing time** scales with number of DICOM files
- Consider using **batch processing** for very large series

## Current Limits Summary

| Component | Default Limit | Configurable |
|-----------|---------------|--------------|
| Backend (FastAPI) | 500 MB | Yes (via `.env`) |
| Streamlit Frontend | 200 MB | Yes (via `config.toml`) |
| API Client Timeout | 600 seconds | Yes (in code) |

## Troubleshooting

### "413 Request Entity Too Large"

- Check file size: `ls -lh your_file.zip`
- Verify backend config: Check `.env` for `MAX_UPLOAD_SIZE_MB`
- Restart backend after config changes

### Streamlit Upload Fails

- Check Streamlit config: `~/.streamlit/config.toml`
- Try uploading via API directly
- Check browser console for errors

### Timeout Errors

- Increase API client timeout (currently 600 seconds)
- For very large files, consider chunked upload (future enhancement)
