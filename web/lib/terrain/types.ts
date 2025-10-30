export interface DemDataset {
  id: string;
  name: string;
  description: string;
  cellSizeFt: number;
  gridSize: [number, number]; // [cols, rows]
  originFt: [number, number]; // [x, y] origin in feet
  elevationsFt: number[][]; // row-major heights in feet AMSL
}

export interface PathVertex {
  x: number;
  y: number;
  altitudeFt: number;
  phase?: string;
}

export interface SamplerConfig {
  discoveryIntervalFt: number;
  denseIntervalFt: number;
  mediumIntervalFt: number;
  sparseIntervalFt: number;
  gradMediumFtPer100: number;
  gradHighFtPer100: number;
  gradCriticalFtPer100: number;
  discoveryFraction: number;
  minSafetySpacingFt: number;
  safetyBufferFt: number;
}

export interface AglConstraints {
  minAglFt?: number;
  maxAglFt?: number;
}

export interface SampledPoint {
  x: number;
  y: number;
  distanceFt: number;
  groundFt: number;
  source: 'discovery' | 'refinement';
  gradientFtPer100?: number;
  curvatureFtPer100?: number;
  segmentIndex?: number;
}

export interface Hazard {
  x: number;
  y: number;
  distanceFt: number;
  groundFt: number;
  severity: number;
  gradientFtPer100: number;
  curvatureFtPer100: number;
  segmentIndex: number;
  description: string;
}

export interface TerrainSamplerMetrics {
  discoveryPointsUsed: number;
  refinementPointsUsed: number;
  totalPointsUsed: number;
  hazardsDetected: number;
  safetyWaypoints: number;
}

export interface SafetyWaypoint {
  x: number;
  y: number;
  altitudeFt: number;
  groundFt: number;
  segmentIndex: number;
  distanceFt: number;
  reason: string;
  severity: number;
}

export interface TerrainSamplingResult {
  samples: SampledPoint[];
  refinementSamples: SampledPoint[];
  hazards: Hazard[];
  safetyWaypoints: SafetyWaypoint[];
  metrics: TerrainSamplerMetrics;
}
