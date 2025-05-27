# API Documentation

## Drone Path API

**Endpoint**: `/DronePathREST`
**Method**: POST

Generates optimized drone flight paths for different property types.

### Request Body
```json
{
  "propertyType": "standard|ranch",
  "coordinates": [...],
  "other_params": "..."
}
```

## File Upload API

**Endpoints**:
- `/start-multipart-upload` - Initiate file upload
- `/get-presigned-url` - Get upload URL for file part
- `/complete-multipart-upload` - Complete the upload
- `/save-submission` - Save metadata and send notifications

All endpoints use POST method and support CORS. 