import worker from '../infrastructure/cloudflare/spaces-viewer/src/index.ts';

type StoredObject = {
  body: Uint8Array;
  httpMetadata: {
    contentType?: string;
    cacheControl?: string;
  };
  etag: string;
};

class FakeR2Bucket {
  private readonly objects = new Map<string, StoredObject>();

  async head(key: string): Promise<{ size: number } | null> {
    const object = this.objects.get(key);
    if (!object) return null;
    return { size: object.body.byteLength };
  }

  async put(
    key: string,
    value: ArrayBuffer | Uint8Array,
    options?: { httpMetadata?: { contentType?: string; cacheControl?: string } }
  ): Promise<void> {
    const bytes = value instanceof Uint8Array ? value : new Uint8Array(value);
    const etag = `"${key.length.toString(16)}-${bytes.byteLength.toString(16)}-${this.objects.size.toString(16)}"`;
    this.objects.set(key, {
      body: bytes,
      httpMetadata: {
        contentType: options?.httpMetadata?.contentType,
        cacheControl: options?.httpMetadata?.cacheControl,
      },
      etag,
    });
  }

  async get(key: string): Promise<any | null> {
    const object = this.objects.get(key);
    if (!object) return null;

    return {
      body: object.body,
      httpMetadata: object.httpMetadata,
      httpEtag: object.etag,
      writeHttpMetadata: (headers: Headers) => {
        if (object.httpMetadata.contentType) {
          headers.set('Content-Type', object.httpMetadata.contentType);
        }
        if (object.httpMetadata.cacheControl) {
          headers.set('Cache-Control', object.httpMetadata.cacheControl);
        }
      },
    };
  }
}

type TestEnv = {
  SPACES_BUCKET: FakeR2Bucket;
  SPACES_HOST: string;
  SPACES_PATH_PREFIX: string;
  SPACES_PUBLISH_TOKEN: string;
};

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
}

async function publish(env: TestEnv, payload: {
  title: string;
  html: string;
  slug?: string;
  mode?: 'create' | 'update' | string;
}) {
  const formData = new FormData();
  formData.set('title', payload.title);
  formData.set('file', new File([payload.html], 'index.html', { type: 'text/html' }));
  if (payload.slug) formData.set('slug', payload.slug);
  if (payload.mode) formData.set('mode', payload.mode);

  const response = await worker.fetch(
    new Request('https://spcprt.com/spaces/publish', {
      method: 'POST',
      headers: { 'X-Spaces-Token': env.SPACES_PUBLISH_TOKEN },
      body: formData,
    }),
    env as any
  );

  const data = await response.json().catch(() => ({}));
  return { response, data };
}

async function fetchViewer(env: TestEnv, slug: string): Promise<string> {
  const response = await worker.fetch(
    new Request(`https://spcprt.com/spaces/${slug}`, { method: 'GET' }),
    env as any
  );
  assert(response.status === 200, `Expected viewer 200 for ${slug}, got ${response.status}`);
  return response.text();
}

async function run() {
  const env: TestEnv = {
    SPACES_BUCKET: new FakeR2Bucket(),
    SPACES_HOST: 'spcprt.com',
    SPACES_PATH_PREFIX: '/spaces',
    SPACES_PUBLISH_TOKEN: 'test-token',
  };

  // 1) Base publish creates a slug and stores initial content.
  const first = await publish(env, {
    title: 'Red Arrow Ranch',
    html: '<html><body>v1</body></html>',
    mode: 'create',
  });
  assert(first.response.status === 200, `Expected create 200, got ${first.response.status}`);
  const createdSlug = first.data?.slug;
  assert(typeof createdSlug === 'string' && createdSlug.length > 0, 'Expected created slug');
  assert(createdSlug.startsWith('red-arrow-ranch'), `Unexpected slug from create: ${createdSlug}`);
  assert((await fetchViewer(env, createdSlug)).includes('v1'), 'Expected v1 content after create');

  // 2) Explicit update mode overwrites the exact existing slug.
  const update = await publish(env, {
    title: 'Ignored for update',
    slug: createdSlug,
    mode: 'update',
    html: '<html><body>v2</body></html>',
  });
  assert(update.response.status === 200, `Expected update 200, got ${update.response.status}`);
  assert(update.data?.slug === createdSlug, 'Update should return the same slug');
  assert(update.data?.updated === true, 'Update should report updated=true');
  assert((await fetchViewer(env, createdSlug)).includes('v2'), 'Expected v2 content after update');

  // 3) Legacy behavior: slug without mode still updates existing slug (backward-compatible).
  const legacyUpdate = await publish(env, {
    title: 'Legacy update payload',
    slug: createdSlug,
    html: '<html><body>v3</body></html>',
  });
  assert(legacyUpdate.response.status === 200, `Expected legacy update 200, got ${legacyUpdate.response.status}`);
  assert(legacyUpdate.data?.slug === createdSlug, 'Legacy update should keep slug');
  assert((await fetchViewer(env, createdSlug)).includes('v3'), 'Expected v3 content after legacy update');

  // 4) Update mode with missing slug is rejected.
  const missingSlugUpdate = await publish(env, {
    title: 'Missing slug update',
    mode: 'update',
    html: '<html><body>x</body></html>',
  });
  assert(missingSlugUpdate.response.status === 400, `Expected update missing slug 400, got ${missingSlugUpdate.response.status}`);

  // 5) Update mode with non-existent slug is rejected.
  const missingTargetUpdate = await publish(env, {
    title: 'Missing target update',
    slug: 'does-not-exist',
    mode: 'update',
    html: '<html><body>x</body></html>',
  });
  assert(missingTargetUpdate.response.status === 404, `Expected missing target 404, got ${missingTargetUpdate.response.status}`);

  // 6) Invalid slug input is rejected (no silent random suffix fallback).
  const invalidSlug = await publish(env, {
    title: 'Invalid slug',
    slug: 'https://spcprt.com/spaces/not_valid_slug',
    mode: 'update',
    html: '<html><body>x</body></html>',
  });
  assert(invalidSlug.response.status === 400, `Expected invalid slug 400, got ${invalidSlug.response.status}`);

  // 7) Explicit create mode cannot clobber an existing slug.
  const createCollision = await publish(env, {
    title: 'Collision create',
    slug: createdSlug,
    mode: 'create',
    html: '<html><body>collision</body></html>',
  });
  assert(createCollision.response.status === 409, `Expected create collision 409, got ${createCollision.response.status}`);

  // 8) Invalid mode is rejected.
  const invalidMode = await publish(env, {
    title: 'Invalid mode',
    mode: 'replace',
    html: '<html><body>x</body></html>',
  });
  assert(invalidMode.response.status === 400, `Expected invalid mode 400, got ${invalidMode.response.status}`);

  console.log(`PASS: spaces-viewer update regression for slug ${createdSlug}`);
}

run().catch((error) => {
  console.error('FAIL:', error instanceof Error ? error.message : error);
  process.exit(1);
});
