// Centralized API configuration for Spaceport
// All API endpoints are configured via environment variables for easy management

function ensureWaitlistEndpoint(rawUrl: string | undefined): string {
  if (!rawUrl) return '';
  const trimmed = rawUrl.trim();
  if (!trimmed) return '';

  try {
    const url = new URL(trimmed);
    const segments = url.pathname.split('/').filter(Boolean);
    const lowerSegment = 'waitlist';

    if (!segments.some(segment => segment.toLowerCase() === lowerSegment)) {
      segments.push(lowerSegment);
    }

    url.pathname = segments.length ? `/${segments.join('/')}` : '/waitlist';
    return url.toString();
  } catch {
    const segment = 'waitlist';
    const parts = trimmed.match(/^([^?#]+)(.*)$/);
    const base = (parts?.[1] || trimmed).replace(/\/+$/, '');
    const suffix = parts?.[2] || '';

    if (base.toLowerCase().endsWith(`/${segment}`)) {
      return `${base}${suffix}`;
    }

    return `${base}/${segment}${suffix}`;
  }
}

export const API_CONFIG = {
  // Projects API - User project management
  PROJECTS_API_URL: process.env.NEXT_PUBLIC_PROJECTS_API_URL!,
  
  // Drone Path API - Flight path optimization and CSV generation
  DRONE_PATH_API_URL: process.env.NEXT_PUBLIC_DRONE_PATH_API_URL!,
  
  // File Upload API - File upload operations
  FILE_UPLOAD_API_URL: process.env.NEXT_PUBLIC_FILE_UPLOAD_API_URL!,
  
  // Waitlist API - User waitlist submissions
  WAITLIST_API_URL: ensureWaitlistEndpoint(process.env.NEXT_PUBLIC_WAITLIST_API_URL),
  
  // ML Pipeline API - ML processing operations
  ML_PIPELINE_API_URL: process.env.NEXT_PUBLIC_ML_PIPELINE_API_URL!,
  
  // Beta Access Admin API - Employee beta access management
  BETA_ACCESS_API_URL: process.env.NEXT_PUBLIC_BETA_ACCESS_API_URL || '',

  // Model Delivery Admin API - Employee-managed deliverables
  MODEL_DELIVERY_API_URL: process.env.NEXT_PUBLIC_MODEL_DELIVERY_API_URL || '',
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
  
  // Beta Access Admin API endpoints
  betaAccess: {
    checkPermission: () => `${API_CONFIG.BETA_ACCESS_API_URL}/admin/beta-access/check-permission`,
    sendInvitation: () => `${API_CONFIG.BETA_ACCESS_API_URL}/admin/beta-access/send-invitation`,
  },

  // Model Delivery Admin API endpoints
  modelDelivery: {
    checkPermission: () => `${API_CONFIG.MODEL_DELIVERY_API_URL}/admin/model-delivery/check-permission`,
    listProjects: () => `${API_CONFIG.MODEL_DELIVERY_API_URL}/admin/model-delivery/list-projects`,
    send: () => `${API_CONFIG.MODEL_DELIVERY_API_URL}/admin/model-delivery/send`,
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
