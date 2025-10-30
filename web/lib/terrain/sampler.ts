import { sampleDemElevation } from './dems';
import type {
  AglConstraints,
  DemDataset,
  Hazard,
  PathVertex,
  SamplerConfig,
  SampledPoint,
  SafetyWaypoint,
  TerrainSamplerMetrics,
  TerrainSamplingResult,
} from './types';

const DEFAULT_CONFIG: SamplerConfig = {
  discoveryIntervalFt: 450,
  denseIntervalFt: 30,
  mediumIntervalFt: 140,
  sparseIntervalFt: 300,
  gradMediumFtPer100: 10,
  gradHighFtPer100: 20,
  gradCriticalFtPer100: 40,
  discoveryFraction: 0.25,
  minSafetySpacingFt: 50,
  safetyBufferFt: 100,
};

function distance2d(ax: number, ay: number, bx: number, by: number): number {
  const dx = bx - ax;
  const dy = by - ay;
  return Math.hypot(dx, dy);
}

function computePathDistances(path: PathVertex[]): number[] {
  const distances = [0];
  for (let i = 1; i < path.length; i++) {
    const prev = path[i - 1];
    const curr = path[i];
    distances.push(distances[i - 1] + distance2d(prev.x, prev.y, curr.x, curr.y));
  }
  return distances;
}

function interpolateAlongPath(
  path: PathVertex[],
  distances: number[],
  targetDistance: number,
): { x: number; y: number; segmentIndex: number; fraction: number } {
  if (targetDistance <= 0) {
    return { x: path[0].x, y: path[0].y, segmentIndex: 0, fraction: 0 };
  }
  if (targetDistance >= distances[distances.length - 1]) {
    const last = path.length - 1;
    return { x: path[last].x, y: path[last].y, segmentIndex: last - 1, fraction: 1 };
  }
  for (let i = 1; i < distances.length; i++) {
    if (targetDistance <= distances[i]) {
      const startDist = distances[i - 1];
      const segLength = Math.max(distances[i] - startDist, 1e-6);
      const fraction = (targetDistance - startDist) / segLength;
      const start = path[i - 1];
      const end = path[i];
      return {
        x: start.x + (end.x - start.x) * fraction,
        y: start.y + (end.y - start.y) * fraction,
        segmentIndex: i - 1,
        fraction,
      };
    }
  }
  const last = path.length - 1;
  return { x: path[last].x, y: path[last].y, segmentIndex: last - 1, fraction: 1 };
}

function smoothSeries(values: number[], window = 5): number[] {
  if (values.length <= 2) return values.slice();
  if (window % 2 === 0) window += 1;
  const radius = Math.floor(window / 2);
  const result: number[] = [];
  for (let i = 0; i < values.length; i++) {
    const start = Math.max(0, i - radius);
    const end = Math.min(values.length, i + radius + 1);
    const slice = values.slice(start, end).sort((a, b) => a - b);
    const median = slice[Math.floor(slice.length / 2)];
    const mean = slice.reduce((acc, val) => acc + val, 0) / slice.length;
    result.push((median + mean) / 2);
  }
  return result;
}

function calculateGradients(elevations: number[], distances: number[], windowFt: number): number[] {
  const gradients: number[] = [];
  for (let i = 0; i < elevations.length; i++) {
    let left = i;
    while (left > 0 && distances[i] - distances[left] < windowFt) left--;
    let right = i;
    while (right < elevations.length - 1 && distances[right] - distances[i] < windowFt) right++;
    if (left === i || right === i) {
      gradients.push(0);
      continue;
    }
    const rise = elevations[right] - elevations[left];
    const run = Math.max(distances[right] - distances[left], 1);
    gradients.push((rise / run) * 100);
  }
  return gradients;
}

function calculateCurvature(gradients: number[], distances: number[]): number[] {
  const curvatures: number[] = [];
  for (let i = 0; i < gradients.length; i++) {
    if (i === 0 || i === gradients.length - 1) {
      curvatures.push(0);
      continue;
    }
    const deltaDistance = Math.max(distances[i + 1] - distances[i - 1], 1);
    curvatures.push(((gradients[i + 1] - gradients[i - 1]) / deltaDistance) * 100);
  }
  return curvatures;
}

function sparseDiscoveryScan(
  path: PathVertex[],
  dem: DemDataset,
  cfg: SamplerConfig,
): { samples: SampledPoint[]; used: number } {
  if (path.length < 2) return { samples: [], used: 0 };
  const distances = computePathDistances(path);
  const totalLength = distances[distances.length - 1];
  if (totalLength <= 0) return { samples: [], used: 0 };
  const interval = Math.max(cfg.discoveryIntervalFt, 1);
  const targets: number[] = [0];
  let cursor = interval;
  while (cursor < totalLength) {
    targets.push(cursor);
    cursor += interval;
  }
  if (targets[targets.length - 1] !== totalLength) {
    targets.push(totalLength);
  }
  const samples: SampledPoint[] = targets.map((target) => {
    const pos = interpolateAlongPath(path, distances, target);
    const groundFt = sampleDemElevation(dem, pos.x, pos.y);
    return {
      x: pos.x,
      y: pos.y,
      distanceFt: target,
      groundFt,
      source: 'discovery',
      segmentIndex: pos.segmentIndex,
    };
  });
  return { samples, used: samples.length };
}

interface SegmentRisk {
  severity: number;
  segmentIndex: number;
  startDistanceFt: number;
  endDistanceFt: number;
  maxGradient: number;
  maxCurvature: number;
}

function rankSegments(samples: SampledPoint[], cfg: SamplerConfig): SegmentRisk[] {
  const risks: SegmentRisk[] = [];
  for (let i = 0; i < samples.length - 1; i++) {
    const start = samples[i];
    const end = samples[i + 1];
    const grad = Math.max(Math.abs(start.gradientFtPer100 ?? 0), Math.abs(end.gradientFtPer100 ?? 0));
    const curv = Math.max(Math.abs(start.curvatureFtPer100 ?? 0), Math.abs(end.curvatureFtPer100 ?? 0));
    const length = end.distanceFt - start.distanceFt;
    if (length <= 0) continue;
    const severity = grad * 0.7 + curv * 0.3;
    if (severity < cfg.gradMediumFtPer100) continue;
    risks.push({
      severity,
      segmentIndex: i,
      startDistanceFt: start.distanceFt,
      endDistanceFt: end.distanceFt,
      maxGradient: grad,
      maxCurvature: curv,
    });
  }
  return risks.sort((a, b) => b.severity - a.severity);
}

function chooseInterval(maxGradient: number, cfg: SamplerConfig): number {
  if (maxGradient >= cfg.gradCriticalFtPer100) return cfg.denseIntervalFt;
  if (maxGradient >= cfg.gradHighFtPer100) return cfg.mediumIntervalFt;
  if (maxGradient >= cfg.gradMediumFtPer100) return cfg.sparseIntervalFt;
  return cfg.discoveryIntervalFt * 1.5;
}

function hazardsFromDiscovery(samples: SampledPoint[], cfg: SamplerConfig): Hazard[] {
  return samples
    .filter((sample) => {
      const grad = Math.abs(sample.gradientFtPer100 ?? 0);
      const curv = Math.abs(sample.curvatureFtPer100 ?? 0);
      return grad >= cfg.gradMediumFtPer100 || curv >= cfg.gradMediumFtPer100;
    })
    .map((sample) => ({
      x: sample.x,
      y: sample.y,
      distanceFt: sample.distanceFt,
      groundFt: sample.groundFt,
      severity: Math.max(Math.abs(sample.gradientFtPer100 ?? 0), Math.abs(sample.curvatureFtPer100 ?? 0)),
      gradientFtPer100: sample.gradientFtPer100 ?? 0,
      curvatureFtPer100: sample.curvatureFtPer100 ?? 0,
      segmentIndex: sample.segmentIndex ?? 0,
      description: 'Discovery gradient alert',
    }));
}

function detectPeakElevation(
  risk: SegmentRisk,
  path: PathVertex[],
  distances: number[],
  dem: DemDataset,
): { sample: SampledPoint | null; used: number } {
  let left = risk.startDistanceFt;
  let right = risk.endDistanceFt;
  let best: SampledPoint | null = null;
  let used = 0;
  for (let i = 0; i < 4; i += 1) {
    const lMid = left + (right - left) / 3;
    const rMid = right - (right - left) / 3;
    const probes = [lMid, rMid].map((distanceFt) => {
      const pos = interpolateAlongPath(path, distances, distanceFt);
      const groundFt = sampleDemElevation(dem, pos.x, pos.y);
      const sample: SampledPoint = {
        x: pos.x,
        y: pos.y,
        distanceFt,
        groundFt,
        source: 'refinement',
        gradientFtPer100: risk.maxGradient,
        curvatureFtPer100: risk.maxCurvature,
        segmentIndex: risk.segmentIndex,
      };
      return sample;
    });
    used += probes.length;
    for (const sample of probes) {
      if (!best || sample.groundFt > best.groundFt) {
        best = sample;
      }
    }
    if (probes[0].groundFt > probes[1].groundFt) {
      right = rMid;
    } else {
      left = lMid;
    }
  }
  return { sample: best, used };
}

function refineSegments(
  risks: SegmentRisk[],
  path: PathVertex[],
  dem: DemDataset,
  cfg: SamplerConfig,
): { samples: SampledPoint[]; hazards: Hazard[]; used: number } {
  const distances = computePathDistances(path);
  const refinementSamples: SampledPoint[] = [];
  const hazards: Hazard[] = [];
  let used = 0;

  for (const risk of risks) {
    const segmentLength = Math.max(risk.endDistanceFt - risk.startDistanceFt, 1);

    if (risk.maxGradient >= cfg.gradCriticalFtPer100) {
      const { sample, used: peakUsed } = detectPeakElevation(risk, path, distances, dem);
      used += peakUsed;
      if (sample) {
        refinementSamples.push(sample);
        hazards.push({
          x: sample.x,
          y: sample.y,
          distanceFt: sample.distanceFt,
          groundFt: sample.groundFt,
          severity: risk.severity,
          gradientFtPer100: risk.maxGradient,
          curvatureFtPer100: risk.maxCurvature,
          segmentIndex: risk.segmentIndex,
          description: 'Critical gradient refinement peak',
        });
      }
      continue;
    }

    const interval = chooseInterval(risk.maxGradient, cfg);
    const targets: number[] = [];
    let cursor = risk.startDistanceFt + interval / 2;
    while (cursor < risk.endDistanceFt - 1e-6) {
      targets.push(cursor);
      cursor += interval;
    }
    if (!targets.length) {
      continue;
    }
    for (const target of targets) {
      const pos = interpolateAlongPath(path, distances, target);
      const groundFt = sampleDemElevation(dem, pos.x, pos.y);
      const sample: SampledPoint = {
        x: pos.x,
        y: pos.y,
        distanceFt: target,
        groundFt,
        source: 'refinement',
        gradientFtPer100: risk.maxGradient,
        curvatureFtPer100: risk.maxCurvature,
        segmentIndex: risk.segmentIndex,
      };
      refinementSamples.push(sample);
      used += 1;
      hazards.push({
        x: sample.x,
        y: sample.y,
        distanceFt: sample.distanceFt,
        groundFt: sample.groundFt,
        severity: risk.severity,
        gradientFtPer100: risk.maxGradient,
        curvatureFtPer100: risk.maxCurvature,
        segmentIndex: risk.segmentIndex,
        description: 'Risk-weighted refinement sample',
      });
    }
  }

  return { samples: refinementSamples, hazards, used };
}

function generateSafetyWaypoints(
  hazards: Hazard[],
  agl: AglConstraints,
  cfg: SamplerConfig,
): SafetyWaypoint[] {
  if (!hazards.length) return [];
  const minAgl = agl.minAglFt ?? 120;
  const maxAgl = agl.maxAglFt ?? Number.POSITIVE_INFINITY;

  const sorted = hazards.slice().sort((a, b) => b.severity - a.severity);
  const accepted: Hazard[] = [];
  const spacingSq = cfg.minSafetySpacingFt ** 2;

  const sqrDist = (a: Hazard, b: Hazard) => (a.x - b.x) ** 2 + (a.y - b.y) ** 2;

  for (const hazard of sorted) {
    if (
      accepted.some(
        (existing) =>
          sqrDist(existing, hazard) < spacingSq ||
          Math.abs(hazard.distanceFt - existing.distanceFt) < cfg.minSafetySpacingFt,
      )
    ) {
      continue;
    }
    const targetAgl = Math.max(minAgl, cfg.safetyBufferFt);
    const altitudeFt = Math.min(hazard.groundFt + targetAgl, hazard.groundFt + maxAgl);
    accepted.push(hazard);
    hazard.severity = Math.max(hazard.severity, 1);
  }

  return accepted.map((hazard) => {
    const targetAgl = Math.max(minAgl, cfg.safetyBufferFt);
    const altitudeFt = Math.min(hazard.groundFt + targetAgl, hazard.groundFt + (agl.maxAglFt ?? targetAgl));
    return {
      x: hazard.x,
      y: hazard.y,
      altitudeFt,
      groundFt: hazard.groundFt,
      segmentIndex: hazard.segmentIndex,
      distanceFt: hazard.distanceFt,
      reason: hazard.description,
      severity: hazard.severity,
    };
  });
}

export function buildSamplerConfig(overrides?: Partial<SamplerConfig>): SamplerConfig {
  return { ...DEFAULT_CONFIG, ...overrides };
}

export function twoPassAdaptiveSampling(
  path: PathVertex[],
  dem: DemDataset,
  cfg: SamplerConfig,
  agl: AglConstraints,
): TerrainSamplingResult {
  if (path.length < 2) {
    return {
      samples: [],
      refinementSamples: [],
      hazards: [],
      safetyWaypoints: [],
      metrics: {
        discoveryPointsUsed: 0,
        refinementPointsUsed: 0,
        totalPointsUsed: 0,
        hazardsDetected: 0,
        safetyWaypoints: 0,
      },
    };
  }

  const distances = computePathDistances(path);
  const { samples: discoverySamples, used: discoveryUsed } = sparseDiscoveryScan(path, dem, cfg);
  if (!discoverySamples.length) {
    return {
      samples: [],
      refinementSamples: [],
      hazards: [],
      safetyWaypoints: [],
      metrics: {
        discoveryPointsUsed: 0,
        refinementPointsUsed: 0,
        totalPointsUsed: 0,
        hazardsDetected: 0,
        safetyWaypoints: 0,
      },
    };
  }

  const rawElevations = discoverySamples.map((s) => s.groundFt);
  const smoothed = smoothSeries(rawElevations, Math.max(5, Math.round(cfg.discoveryIntervalFt / 50) | 1));
  const gradients = calculateGradients(smoothed, discoverySamples.map((s) => s.distanceFt), cfg.discoveryIntervalFt * 2);
  const curvatures = calculateCurvature(gradients, discoverySamples.map((s) => s.distanceFt));
  discoverySamples.forEach((sample, i) => {
    sample.gradientFtPer100 = gradients[i];
    sample.curvatureFtPer100 = curvatures[i];
  });

  const risks = rankSegments(discoverySamples, cfg);
  const { samples: refinementSamples, hazards: refinementHazards, used: refinementUsed } =
    refineSegments(risks, path, dem, cfg);

  const hazardList = [...hazardsFromDiscovery(discoverySamples, cfg), ...refinementHazards];
  const safetyWaypoints = generateSafetyWaypoints(hazardList, agl, cfg);

  const metrics: TerrainSamplerMetrics = {
    discoveryPointsUsed: discoveryUsed,
    refinementPointsUsed: refinementUsed,
    totalPointsUsed: discoveryUsed + refinementUsed,
    hazardsDetected: hazardList.length,
    safetyWaypoints: safetyWaypoints.length,
  };

  return {
    samples: discoverySamples,
    refinementSamples,
    hazards: hazardList,
    safetyWaypoints,
    metrics,
  };
}
