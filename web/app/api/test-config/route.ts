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
    NEXT_PUBLIC_SUBSCRIPTION_API_URL: process.env.NEXT_PUBLIC_SUBSCRIPTION_API_URL || '',
  };

  return new Response(JSON.stringify({ env }), {
    status: 200,
    headers: { 'content-type': 'application/json; charset=utf-8' },
  });
}
