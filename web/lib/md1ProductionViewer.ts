export const MD1_V18_PRODUCTION_LOD_URL =
  process.env.NEXT_PUBLIC_MD1_V18_PRODUCTION_LOD_URL?.trim() ||
  "https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-r5-v18-splattransform-lod-nosingle-public-1777575472/supersplat_bundle/lod-meta.json";

export const MD1_V18_PRODUCTION_MANIFEST_URL =
  process.env.NEXT_PUBLIC_MD1_V18_PRODUCTION_MANIFEST_URL?.trim() ||
  "https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-r5-v18-splattransform-lod-nosingle-public-1777575472/production_manifest.json";

export const MD1_V18_SFM_URL =
  "https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-r5-v18-sfm-viewer-1776314974/sfm_points_every4.json";

export const MD1_V18_SAMPLED_INSPECTION_URL =
  "https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-r5-v18-viewer-sampled-1777498999/merged_splat_every8_shrink.ply";

export const MD1_V18_RAW_PLY_URL =
  "https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-r5-v18-raw-1777498999/merged_splat.ply";

export const MD1_V18_PROMOTED_ARTIFACT_URI =
  "s3://spaceport-ml-processing-staging/manual-validations/md1-geometry-consistency-r5-teacher-context-v12-sky-v18-20260429110309/output/artifact/model.tar.gz";

export const MD1_V18_SOURCE_PLY_URI =
  "s3://spaceport-ml-processing/compressed/md1-r5-v18-raw-1777498999/merged_splat.ply";

export const MD1_V18_LINEAGE = {
  promotedGaussianCount: 8423868,
  sourceGaussianCount: 8789634,
  droppedGaussianCount: 365766,
  sourcePlyBytes: 876082905,
  fullSogsBundleBytes: 97851045,
  sampledInspectionCount: 1052984,
  sfmSourcePointCount: 1312804,
  sfmSampledPointCount: 328201,
  sfmCameraCount: 2143,
  sfmSourceCameraCount: 2157,
} as const;

export const MD1_V18_COMPUTE = {
  jobName: "md1-r5-14tile-2k-1777240767-tiled",
  instanceType: "ml.g5.2xlarge",
  billableSeconds: 171467,
  billableHours: 47.63,
  hourlyUsd: 1.515,
  estimatedUsd: 72.16,
  tileTrainingHours: 46.71,
  overheadHours: 0.92,
} as const;

export const MD1_V18_COMPRESSION = {
  jobName: "md1-v18-splat-lod-nosingle-1777575472",
  stoppedSupersededJobName: "md1-v18-splat-lod-1777573315",
  compressor: "@playcanvas/splat-transform",
  compressorVersion: "1.10.2",
  imageUri:
    "975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/compressor@sha256:645fd74b9217fc8441f242d8b89aefb36ef9c88192bf006ade3cfeb355bd4de3",
  mode: "validated-lod-only",
  lodLevels: 4,
  chunkFiles: 44,
  objectCount: 357,
  byteSize: 165902596,
} as const;

export const MD1_STREAMING_CONFIG = {
  splatBudgetDesktop: 3_000_000,
  splatBudgetMobile: 1_000_000,
  lodRangeMinDesktop: 0,
  lodRangeMinMobile: 2,
  lodRangeMaxDesktop: 3,
  lodRangeMaxMobile: 3,
  lodDistancesDesktop: [24, 90, 220, 520],
  lodDistancesMobile: [10, 36, 90, 220],
  lodUnderfillLimit: 0,
  lodUpdateDistance: 0.5,
  lodUpdateAngle: 1,
  colorUpdateDistance: 0.1,
  colorUpdateAngle: 1,
  colorUpdateDistanceLodScale: 1.4,
  colorUpdateAngleLodScale: 1.4,
} as const;

export function isProbablyMobileViewport() {
  if (typeof window === "undefined") {
    return false;
  }
  const ua = window.navigator.userAgent.toLowerCase();
  return /iphone|ipad|android|mobile/.test(ua) || window.innerWidth <= 768;
}

export function buildMd1ViewerConfigPayload(
  config = MD1_STREAMING_CONFIG,
  mobileOverride?: boolean,
) {
  const mobile = mobileOverride ?? isProbablyMobileViewport();
  const base = {
    splatBudget: mobile ? config.splatBudgetMobile : config.splatBudgetDesktop,
    lodRangeMin: mobile ? config.lodRangeMinMobile : config.lodRangeMinDesktop,
    lodRangeMax: mobile ? config.lodRangeMaxMobile : config.lodRangeMaxDesktop,
    lodDistances: mobile ? config.lodDistancesMobile : config.lodDistancesDesktop,
  };
  return {
    type: "sogs:config" as const,
    ...base,
    lodUnderfillLimit: config.lodUnderfillLimit,
    lodUpdateDistance: config.lodUpdateDistance,
    lodUpdateAngle: config.lodUpdateAngle,
    colorUpdateDistance: config.colorUpdateDistance,
    colorUpdateAngle: config.colorUpdateAngle,
    colorUpdateDistanceLodScale: config.colorUpdateDistanceLodScale,
    colorUpdateAngleLodScale: config.colorUpdateAngleLodScale,
  };
}

export type Md1ViewerConfigPayload = ReturnType<typeof buildMd1ViewerConfigPayload>;

export function withMd1ViewerOverrides(
  payload: Md1ViewerConfigPayload,
  overrides: {
    splatBudget?: number | null;
    lodRangeMin?: number | null;
    lodRangeMax?: number | null;
  },
) {
  return {
    ...payload,
    splatBudget: overrides.splatBudget ?? payload.splatBudget,
    lodRangeMin: overrides.lodRangeMin ?? payload.lodRangeMin,
    lodRangeMax: overrides.lodRangeMax ?? payload.lodRangeMax,
  };
}
