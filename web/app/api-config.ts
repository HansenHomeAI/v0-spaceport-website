// Centralized API configuration for Spaceport
// All API endpoints are configured via environment variables for easy management

export const API_CONFIG = {
  // Projects API - User project management
  PROJECTS_API_URL: process.env.NEXT_PUBLIC_PROJECTS_API_URL || 'https://34ap3qgem7.execute-api.us-west-2.amazonaws.com/prod/projects',
  
  // Drone Path API - Flight path optimization and CSV generation
  DRONE_PATH_API_URL: process.env.NEXT_PUBLIC_DRONE_PATH_API_URL || 'https://7bidiow2t9.execute-api.us-west-2.amazonaws.com/prod',
  
  // File Upload API - File upload operations
  FILE_UPLOAD_API_URL: process.env.NEXT_PUBLIC_FILE_UPLOAD_API_URL || 'https://o7d0i4to5a.execute-api.us-west-2.amazonaws.com/prod',
  
  // Waitlist API - User waitlist submissions
  WAITLIST_API_URL: process.env.NEXT_PUBLIC_WAITLIST_API_URL || 'https://o7d0i4to5a.execute-api.us-west-2.amazonaws.com/prod/waitlist',
  
  // ML Pipeline API - ML processing operations
  ML_PIPELINE_API_URL: process.env.NEXT_PUBLIC_ML_PIPELINE_API_URL || 'https://2vulsewyl5.execute-api.us-west-2.amazonaws.com/prod',
} as const;

// Individual API endpoint builders
export const buildApiUrl = {
  // Projects API endpoints
  projects: () => API_CONFIG.PROJECTS_API_URL,
  
  // Drone Path API endpoints
  dronePath: {
    optimizeSpiral: () => `${API_CONFIG.DRONE_PATH_API_URL}/api/optimize-spiral`,
    elevation: () => `${API_CONFIG.DRONE_PATH_API_URL}/api/elevation`,
    csv: () => `${API_CONFIG.DRONE_PATH_API_URL}/api/csv`,
    batteryCsv: (batteryId: string) => `${API_CONFIG.DRONE_PATH_API_URL}/api/csv/battery/${batteryId}`,
    legacy: () => `${API_CONFIG.DRONE_PATH_API_URL}/DronePathREST`,
  },
  
  // File Upload API endpoints
  fileUpload: {
    startUpload: () => `${API_CONFIG.FILE_UPLOAD_API_URL}/start-multipart-upload`,
    getPresignedUrl: () => `${API_CONFIG.FILE_UPLOAD_API_URL}/get-presigned-url`,
    completeUpload: () => `${API_CONFIG.FILE_UPLOAD_API_URL}/complete-multipart-upload`,
    saveSubmission: () => `${API_CONFIG.FILE_UPLOAD_API_URL}/save-submission`,
  },
  
  // Waitlist API endpoints
  waitlist: () => API_CONFIG.WAITLIST_API_URL,
  
  // ML Pipeline API endpoints
  mlPipeline: {
    startJob: () => `${API_CONFIG.ML_PIPELINE_API_URL}/start-job`,
    stopJob: () => `${API_CONFIG.ML_PIPELINE_API_URL}/stop-job`,
  },
} as const;

// Legacy compatibility exports (for existing code)
export const API_ENDPOINTS = {
  DRONE_PATH: buildApiUrl.dronePath.legacy(),
  START_UPLOAD: buildApiUrl.fileUpload.startUpload(),
  GET_PRESIGNED_URL: buildApiUrl.fileUpload.getPresignedUrl(),
  COMPLETE_UPLOAD: buildApiUrl.fileUpload.completeUpload(),
  SAVE_SUBMISSION: buildApiUrl.fileUpload.saveSubmission(),
  WAITLIST: buildApiUrl.waitlist(),
} as const;

export const ENHANCED_API_BASE = API_CONFIG.DRONE_PATH_API_URL;
export const API_UPLOAD = {
  START_UPLOAD: buildApiUrl.fileUpload.startUpload(),
  GET_PRESIGNED_URL: buildApiUrl.fileUpload.getPresignedUrl(),
  COMPLETE_UPLOAD: buildApiUrl.fileUpload.completeUpload(),
  SAVE_SUBMISSION: buildApiUrl.fileUpload.saveSubmission(),
} as const;
