# 🔌 API Reference

## ML Pipeline API

### Start ML Processing Job
**Endpoint**: `POST /start-job`  
**URL**: `https://3xzfdyvwpd.execute-api.us-west-2.amazonaws.com/prod/start-job`

#### Request Body
```json
{
  "s3Url": "s3://bucket-name/path/to/images.zip",
  "email": "user@example.com",
  "pipelineStep": "sfm" | "3dgs" | "compression"
}
```

#### Response
```json
{
  "jobId": "uuid-job-id",
  "executionArn": "arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline:execution-uuid",
  "message": "ML processing job started successfully"
}
```

#### Pipeline Steps
- **`sfm`**: Complete pipeline (SfM → 3DGS → Compression)
- **`3dgs`**: 3DGS training only (requires existing SfM output)  
- **`compression`**: Compression only (requires existing 3DGS output)

### Drone Path API
**Endpoint**: `POST /drone-path`
- Calculates optimal drone flight paths for image capture
- Returns trajectory coordinates and timing

## Error Responses
All endpoints return standard HTTP status codes with descriptive error messages.

## Authentication
Currently uses API Gateway without authentication. Consider adding API keys for production use.

## File Upload API

**Endpoints**:
- `/start-multipart-upload` - Initiate file upload
- `/get-presigned-url` - Get upload URL for file part
- `/complete-multipart-upload` - Complete the upload
- `/save-submission` - Save metadata and send notifications

All endpoints use POST method and support CORS. 