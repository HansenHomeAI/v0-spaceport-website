export const runtime = 'edge';

export async function POST(request: Request): Promise<Response> {
  const contentType = request.headers.get('content-type') || '';
  let data: Record<string, string> = {};
  if (contentType.includes('application/json')) {
    data = await request.json().catch(() => ({}));
  } else if (contentType.includes('application/x-www-form-urlencoded') || contentType.includes('multipart/form-data')) {
    const form = await request.formData();
    for (const [k, v] of form.entries()) {
      data[k] = typeof v === 'string' ? v : '';
    }
  }

  const { email, password, action } = data;

  if (!email || !password) {
    return new Response(JSON.stringify({
      error: 'Email and password are required'
    }), {
      status: 400,
      headers: { 'content-type': 'application/json; charset=utf-8' },
    });
  }

  try {
    // Import Amplify dynamically to avoid SSR issues
    const { Auth } = await import('aws-amplify');

    if (action === 'test-invite-flow') {
      // Test the complete invite flow simulation
      try {
        // Try to sign in with the provided credentials
        const signInResult = await Auth.signIn(email, password);

        if (signInResult.challengeName === 'NEW_PASSWORD_REQUIRED') {
          return new Response(JSON.stringify({
            success: true,
            challenge: 'NEW_PASSWORD_REQUIRED',
            message: 'User exists and requires password setup. This is expected for invited users.',
            nextSteps: [
              'User should be prompted to set a new password',
              'User should set their preferred username',
              'Complete the challenge with Auth.completeNewPassword()'
            ]
          }), {
            status: 200,
            headers: { 'content-type': 'application/json; charset=utf-8' },
          });
        } else {
          return new Response(JSON.stringify({
            success: true,
            message: 'User signed in successfully without requiring password setup',
            user: {
              username: signInResult.username,
              attributes: signInResult.attributes
            }
          }), {
            status: 200,
            headers: { 'content-type': 'application/json; charset=utf-8' },
          });
        }
      } catch (signInError: any) {
        return new Response(JSON.stringify({
          error: signInError.message,
          code: signInError.code || signInError.name,
          details: {
            message: 'Sign in attempt failed',
            suggestion: 'Check if the email and password are correct'
          }
        }), {
          status: 400,
          headers: { 'content-type': 'application/json; charset=utf-8' },
        });
      }
    }

    // Default action: basic sign in test
    const result = await Auth.signIn(email, password);

    return new Response(JSON.stringify({
      success: true,
      result: {
        username: result.username,
        challengeName: result.challengeName,
        attributes: result.attributes
      }
    }), {
      status: 200,
      headers: { 'content-type': 'application/json; charset=utf-8' },
    });

  } catch (error: any) {
    return new Response(JSON.stringify({
      error: error.message,
      code: error.code || error.name,
      stack: process.env.NODE_ENV === 'development' ? error.stack : undefined
    }), {
      status: 500,
      headers: { 'content-type': 'application/json; charset=utf-8' },
    });
  }
}