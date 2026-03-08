const SPACEPORT_ML_S3_HOST_RE =
  /^spaceport-ml-processing(?:-[a-z0-9-]+)?\.s3(?:\.us-west-2)?\.amazonaws\.com$/;

export const isSpaceportMlS3Host = (host) => SPACEPORT_ML_S3_HOST_RE.test(host);

export const buildProxyPath = (url) => {
  const base = `${url.protocol}//${url.host}`;
  const encodedBase = base.replace("://", ":/");
  return `/api/sogs-proxy/${encodedBase}${url.pathname}${url.search}`;
};
