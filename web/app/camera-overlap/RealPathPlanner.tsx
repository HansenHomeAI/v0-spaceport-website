"use client";

import JSZip from "jszip";
import { useEffect, useMemo, useState } from "react";
import { buildApiUrl } from "../api-config";
import { downloadBlob } from "../../lib/flightConverter";
import {
  averageRealPathOverlapIou,
  type RealPathBatteryExportResponse,
  type RealPathOptimizeResponse,
  type RealPathPreviewBattery,
  type SpinPathOverlapConfig,
} from "../../lib/realPathSpin";
import RealPathMap from "./RealPathMap";
import styles from "./page.module.css";

type RealPathPlannerProps = {
  overlapConfig: SpinPathOverlapConfig;
};

function parseOptionalNumber(value: string): number | undefined {
  const trimmed = value.trim();
  if (!trimmed) {
    return undefined;
  }

  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : undefined;
}

function formatFeet(value: number): string {
  return `${Math.round(value).toLocaleString()} ft`;
}

function formatMph(value: number | undefined): string {
  return value === undefined ? "0.0 mph" : `${value.toFixed(1)} mph`;
}

function formatStageSpeedSummary(values: number[] | undefined): string {
  if (!values?.length) {
    return "0.0 mph";
  }
  if (values.length === 1) {
    return formatMph(values[0]);
  }
  return `${values[0].toFixed(1)} -> ${values[values.length - 1].toFixed(1)} mph`;
}

function selectedPreviewBattery(
  result: RealPathOptimizeResponse | null,
  selectedBatteryIndex: number | null,
): RealPathPreviewBattery | null {
  if (!result) {
    return null;
  }

  return result.previewBatteries.find((battery) => battery.batteryIndex === selectedBatteryIndex)
    ?? result.previewBatteries[0]
    ?? null;
}

export default function RealPathPlanner({ overlapConfig }: RealPathPlannerProps) {
  const [center, setCenter] = useState("39.739200, -104.990300");
  const [batteryMinutes, setBatteryMinutes] = useState("20");
  const [batteries, setBatteries] = useState("2");
  const [minHeight, setMinHeight] = useState("120");
  const [maxHeight, setMaxHeight] = useState("360");
  const [formToTerrain, setFormToTerrain] = useState(false);
  const [minExpansionDist, setMinExpansionDist] = useState("");
  const [maxExpansionDist, setMaxExpansionDist] = useState("");
  const [loading, setLoading] = useState(false);
  const [downloadingBatteryIndex, setDownloadingBatteryIndex] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [optimizeResult, setOptimizeResult] = useState<RealPathOptimizeResponse | null>(null);
  const [selectedBatteryIndex, setSelectedBatteryIndex] = useState<number | null>(null);
  const [latestExport, setLatestExport] = useState<RealPathBatteryExportResponse | null>(null);

  const selectedBattery = useMemo(
    () => selectedPreviewBattery(optimizeResult, selectedBatteryIndex),
    [optimizeResult, selectedBatteryIndex],
  );
  const selectedBatteryOverlapPct = useMemo(
    () => (selectedBattery ? averageRealPathOverlapIou(selectedBattery.waypoints) * 100 : 0),
    [selectedBattery],
  );

  useEffect(() => {
    if (!optimizeResult?.batterySummaries.length) {
      setSelectedBatteryIndex(null);
      return;
    }

    setSelectedBatteryIndex((current) => current ?? optimizeResult.batterySummaries[0].batteryIndex);
  }, [optimizeResult]);

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    setLatestExport(null);

    try {
      const body: Record<string, unknown> = {
        center: center.trim(),
        batteryMinutes: Number(batteryMinutes),
        batteries: Number(batteries),
        minHeight: Number(minHeight),
        maxHeight: Number(maxHeight),
        formToTerrain,
        overlapConfig,
      };

      const parsedMinExpansion = parseOptionalNumber(minExpansionDist);
      const parsedMaxExpansion = parseOptionalNumber(maxExpansionDist);
      if (parsedMinExpansion !== undefined) {
        body.minExpansionDist = parsedMinExpansion;
      }
      if (parsedMaxExpansion !== undefined) {
        body.maxExpansionDist = parsedMaxExpansion;
      }

      const response = await fetch(buildApiUrl.spinPath.optimize(), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
      });

      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload?.error || "Spin-path optimize failed");
      }

      setOptimizeResult(payload as RealPathOptimizeResponse);
    } catch (caughtError) {
      setOptimizeResult(null);
      setSelectedBatteryIndex(null);
      setError(caughtError instanceof Error ? caughtError.message : "Spin-path optimize failed");
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadBattery = async (batteryIndex: number) => {
    if (!optimizeResult) {
      return;
    }

    setDownloadingBatteryIndex(batteryIndex);
    setError(null);

    try {
      const response = await fetch(buildApiUrl.spinPath.exportBattery(String(batteryIndex)), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          ...optimizeResult.optimizedParams,
          overlapConfig,
        }),
      });

      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload?.error || "Spin-path export failed");
      }

      const exportResult = payload as RealPathBatteryExportResponse;
      setLatestExport(exportResult);

      if (exportResult.stages.length === 1) {
        const stage = exportResult.stages[0];
        downloadBlob(new Blob([stage.csvText], { type: "text/csv" }), stage.filename);
      } else {
        const zip = new JSZip();
        exportResult.stages.forEach((stage) => {
          zip.file(stage.filename, stage.csvText);
        });
        const blob = await zip.generateAsync({ type: "blob" });
        downloadBlob(blob, `battery-${batteryIndex}-litchi-stages.zip`);
      }
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Spin-path export failed");
    } finally {
      setDownloadingBatteryIndex(null);
    }
  };

  return (
    <div className={styles.realPathPlanner} data-testid="real-path-planner">
      <section className={styles.realPathControlCard}>
        <p className={styles.realPathCardEyebrow}>Real Path</p>
        <h2 className={styles.realPathCardTitle}>Generate a curved flat-spin mission</h2>
        <p className={styles.realPathCardSub}>
          Use the current overlap settings to build a real drone path, preview it on Mapbox, and export staged Litchi CSVs without forcing a waypoint at every capture.
        </p>

        <label className={styles.realPathField}>
          <span>Center coordinates</span>
          <input
            data-testid="real-path-center-input"
            placeholder="39.739200, -104.990300"
            value={center}
            onChange={(event) => setCenter(event.target.value)}
          />
        </label>

        <div className={styles.realPathFieldGrid}>
          <label className={styles.realPathField}>
            <span>Battery minutes</span>
            <input
              data-testid="real-path-battery-minutes"
              type="number"
              min={1}
              max={60}
              value={batteryMinutes}
              onChange={(event) => setBatteryMinutes(event.target.value)}
            />
          </label>
          <label className={styles.realPathField}>
            <span>Battery count</span>
            <input
              data-testid="real-path-battery-count"
              type="number"
              min={1}
              max={12}
              value={batteries}
              onChange={(event) => setBatteries(event.target.value)}
            />
          </label>
        </div>

        <div className={styles.realPathFieldGrid}>
          <label className={styles.realPathField}>
            <span>Min height</span>
            <input
              data-testid="real-path-min-height"
              type="number"
              min={1}
              value={minHeight}
              onChange={(event) => setMinHeight(event.target.value)}
            />
          </label>
          <label className={styles.realPathField}>
            <span>Max height</span>
            <input
              data-testid="real-path-max-height"
              type="number"
              min={1}
              value={maxHeight}
              onChange={(event) => setMaxHeight(event.target.value)}
            />
          </label>
        </div>

        <div className={styles.realPathFieldGrid}>
          <label className={styles.realPathField}>
            <span>Min expansion</span>
            <input
              data-testid="real-path-min-expansion"
              inputMode="decimal"
              placeholder="Optional"
              value={minExpansionDist}
              onChange={(event) => setMinExpansionDist(event.target.value)}
            />
          </label>
          <label className={styles.realPathField}>
            <span>Max expansion</span>
            <input
              data-testid="real-path-max-expansion"
              inputMode="decimal"
              placeholder="Optional"
              value={maxExpansionDist}
              onChange={(event) => setMaxExpansionDist(event.target.value)}
            />
          </label>
        </div>

        <label className={styles.realPathCheckbox}>
          <input
            data-testid="real-path-terrain-toggle"
            type="checkbox"
            checked={formToTerrain}
            onChange={(event) => setFormToTerrain(event.target.checked)}
          />
          <span>Form to terrain</span>
        </label>

        <div className={styles.realPathMetricGrid}>
          <div className={styles.realPathMetric}>
            <span>Capture spacing</span>
            <strong>{overlapConfig.captureSpacingFt.toFixed(1)} ft</strong>
          </div>
          <div className={styles.realPathMetric}>
            <span>Yaw rate</span>
            <strong>{overlapConfig.yawRateDegPerSec.toFixed(1)}°/s</strong>
          </div>
          <div className={styles.realPathMetric}>
            <span>Trigger mode</span>
            <strong>{overlapConfig.captureIntervalUnit === "ft" ? `${overlapConfig.captureDistanceIntervalFt.toFixed(1)} ft` : `${overlapConfig.captureTimeIntervalSeconds.toFixed(2)} s`}</strong>
          </div>
          <div className={styles.realPathMetric}>
            <span>Default gimbal</span>
            <strong>{Math.abs(overlapConfig.defaultPitchDeg).toFixed(0)}° down</strong>
          </div>
        </div>

        <button
          type="button"
          className={styles.realPathGenerateButton}
          data-testid="real-path-generate-btn"
          onClick={handleGenerate}
          disabled={loading}
        >
          {loading ? "Generating..." : "Generate real path"}
        </button>

        {optimizeResult?.optimizationInfo?.adjustments ? (
          <div className={styles.realPathAdjustmentList}>
            {(optimizeResult.optimizationInfo.adjustments as string[]).map((adjustment) => (
              <p key={adjustment}>{adjustment}</p>
            ))}
          </div>
        ) : null}

        {error ? (
          <p className={styles.realPathError} data-testid="real-path-error">
            {error}
          </p>
        ) : null}
      </section>

      <section className={styles.realPathMapCard}>
        <RealPathMap
          batteries={optimizeResult?.previewBatteries ?? []}
          selectedBatteryIndex={selectedBatteryIndex}
        />
      </section>

      {optimizeResult ? (
        <>
          <div className={styles.realPathSelectedSummary}>
            <div>
              <p className={styles.realPathCardEyebrow}>Selected Battery</p>
              <p className={styles.realPathSelectedTitle}>
                {selectedBattery ? `Battery ${selectedBattery.batteryIndex}` : "No battery selected"}
              </p>
            </div>
            <div className={styles.realPathSelectedStats}>
              <span>{selectedBattery ? formatFeet(selectedBattery.telemetry.pathDistanceFeet) : "0 ft"}</span>
              <span>{selectedBatteryOverlapPct.toFixed(0)}% overlap</span>
              <span>{selectedBattery?.telemetry.stageCount ?? 0} stages</span>
              <span>{formatStageSpeedSummary(selectedBattery?.telemetry.stageAverageSpeedMph)} stage speeds</span>
            </div>
          </div>

          <div className={styles.realPathBatteryGrid}>
            {optimizeResult.batterySummaries.map((summary) => {
              const previewBattery = optimizeResult.previewBatteries.find((battery) => battery.batteryIndex === summary.batteryIndex);
              const overlapPct = previewBattery ? averageRealPathOverlapIou(previewBattery.waypoints) * 100 : 0;
              const selected = summary.batteryIndex === selectedBattery?.batteryIndex;

              return (
                <article
                  key={summary.batteryIndex}
                  className={`${styles.realPathBatteryCard} ${selected ? styles.realPathBatteryCardActive : ""}`}
                >
                  <button
                    type="button"
                    className={styles.realPathBatteryPreviewButton}
                    onClick={() => setSelectedBatteryIndex(summary.batteryIndex)}
                  >
                    Preview battery {summary.batteryIndex}
                  </button>
                  <div className={styles.realPathBatteryCardHeader}>
                    <div>
                      <p className={styles.realPathBatteryLabel}>Battery {summary.batteryIndex}</p>
                      <p className={styles.realPathBatteryValue}>{formatFeet(summary.pathDistanceFeet)}</p>
                    </div>
                    <button
                      type="button"
                      data-testid={`real-path-download-battery-${summary.batteryIndex}`}
                      className={styles.realPathDownloadButton}
                      onClick={() => void handleDownloadBattery(summary.batteryIndex)}
                      disabled={downloadingBatteryIndex === summary.batteryIndex}
                    >
                      {downloadingBatteryIndex === summary.batteryIndex
                        ? "Downloading..."
                        : summary.stageCount > 1
                          ? `Download ${summary.stageCount} stages`
                          : "Download CSV"}
                    </button>
                  </div>
                  <div className={styles.realPathBatteryTelemetry}>
                    <span>{summary.waypointCount} waypoints</span>
                    <span>{overlapPct.toFixed(0)}% avg overlap</span>
                    <span>{summary.maxHeadingDeltaDeg.toFixed(1)}° max Δheading</span>
                    <span>{summary.estimatedYawRateDegPerSec.toFixed(1)}°/s yaw</span>
                    <span>{formatStageSpeedSummary(summary.stageAverageSpeedMph)} stage speeds</span>
                    <span>{summary.captureTriggerMode === "ft" ? `${summary.captureDistanceFeet?.toFixed(1) ?? "0.0"} ft trigger` : `${summary.captureIntervalSeconds.toFixed(2)} s trigger`}</span>
                  </div>
                </article>
              );
            })}
          </div>

          {latestExport ? (
            <p className={styles.realPathExportNote} data-testid="real-path-export-note">
              Downloaded battery {latestExport.batteryIndex} with {latestExport.stages.length} stage
              {latestExport.stages.length === 1 ? "" : "s"}.
            </p>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
