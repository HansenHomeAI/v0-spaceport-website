export const runtime = 'edge';

export async function GET(): Promise<Response> {
  const env = {
    NEXT_PUBLIC_PROJECTS_API_URL: process.env.NEXT_PUBLIC_PROJECTS_API_URL || '',
    NEXT_PUBLIC_DRONE_PATH_API_URL: process.env.NEXT_PUBLIC_DRONE_PATH_API_URL || '',
    NEXT_PUBLIC_FILE_UPLOAD_API_URL: process.env.NEXT_PUBLIC_FILE_UPLOAD_API_URL || '',
    NEXT_PUBLIC_WAITLIST_API_URL: process.env.NEXT_PUBLIC_WAITLIST_API_URL || '',
    NEXT_PUBLIC_ML_PIPELINE_API_URL: process.env.NEXT_PUBLIC_ML_PIPELINE_API_URL || '',
    NEXT_PUBLIC_BETA_ACCESS_API_URL: process.env.NEXT_PUBLIC_BETA_ACCESS_API_URL || '',
    NEXT_PUBLIC_MODEL_DELIVERY_ADMIN_API_URL: process.env.NEXT_PUBLIC_MODEL_DELIVERY_ADMIN_API_URL || '',
    NEXT_PUBLIC_EXPLORE_API_URL: process.env.NEXT_PUBLIC_EXPLORE_API_URL || '',
    NEXT_PUBLIC_SUBSCRIPTION_API_URL: process.env.NEXT_PUBLIC_SUBSCRIPTION_API_URL || '',
    AWS_REGION: process.env.AWS_REGION || '',
    ML_DELIVERY_BUCKET_NAME: process.env.ML_DELIVERY_BUCKET_NAME || '',
    HAS_AWS_ACCESS_KEY_ID: Boolean(process.env.AWS_ACCESS_KEY_ID),
    HAS_AWS_SECRET_ACCESS_KEY: Boolean(process.env.AWS_SECRET_ACCESS_KEY),
    HAS_AWS_SESSION_TOKEN: Boolean(process.env.AWS_SESSION_TOKEN),
  };

  return new Response(JSON.stringify({ env }), {
    status: 200,
    headers: { 'content-type': 'application/json; charset=utf-8' },
  });
}
