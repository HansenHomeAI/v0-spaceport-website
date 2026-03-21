import { expect, test } from "@playwright/test";

const optimizeResponse = {
  optimizedParams: {
    slices: 2,
    N: 6,
    r0: 100,
    rHold: 1000,
    center: "39.739200, -104.990300",
    minHeight: 120,
    maxHeight: 360,
    formToTerrain: false,
    actualMinExpansionDist: 140,
    actualMaxExpansionDist: 260,
  },
  optimizationInfo: {
    adjustments: ["Reduced bounces from 8 to 6 to fit battery target"],
  },
  previewPaths: [
    {
      batteryIndex: 1,
      coordinates: [
        [-104.9903, 39.7392],
        [-104.9899, 39.7396],
        [-104.9892, 39.7399],
      ],
    },
    {
      batteryIndex: 2,
      coordinates: [
        [-104.9892, 39.7399],
        [-104.9887, 39.7404],
        [-104.9881, 39.7407],
      ],
    },
  ],
  previewBatteries: [
    {
      batteryIndex: 1,
      telemetry: {
        pathDistanceFeet: 540,
        waypointCount: 42,
        captureSpacingFeet: 12,
        maxHeadingGapFeet: 49.72,
        maxHeadingDeltaDeg: 43.31,
        estimatedYawRateDegPerSec: 90,
        captureArcDeg: 180,
        captureIntervalSeconds: 0.5,
        captureTriggerMode: "s",
        captureDistanceFeet: 0,
        stageCount: 2,
        stageWaypointCounts: [99, 44],
        stageAverageSpeedMph: [17.2, 18.6],
      },
      waypoints: [
        { lat: 39.7392, lng: -104.9903, altitudeFeet: 120, curveFeet: 0, headingDeg: 0, gimbalPitchDeg: -25, distanceFeet: 0 },
        { lat: 39.73935, lng: -104.99015, altitudeFeet: 150, curveFeet: 14, headingDeg: 24, gimbalPitchDeg: -26, distanceFeet: 18 },
        { lat: 39.73955, lng: -104.98995, altitudeFeet: 185, curveFeet: 22, headingDeg: 48, gimbalPitchDeg: -27, distanceFeet: 36 },
        { lat: 39.7398, lng: -104.98955, altitudeFeet: 230, curveFeet: 18, headingDeg: 72, gimbalPitchDeg: -28, distanceFeet: 54 },
      ],
    },
    {
      batteryIndex: 2,
      telemetry: {
        pathDistanceFeet: 610,
        waypointCount: 46,
        captureSpacingFeet: 12,
        maxHeadingGapFeet: 49.72,
        maxHeadingDeltaDeg: 43.31,
        estimatedYawRateDegPerSec: 90,
        captureArcDeg: 180,
        captureIntervalSeconds: 0.5,
        captureTriggerMode: "s",
        captureDistanceFeet: 0,
        stageCount: 1,
        stageWaypointCounts: [78],
        stageAverageSpeedMph: [20.4],
      },
      waypoints: [
        { lat: 39.7399, lng: -104.9892, altitudeFeet: 240, curveFeet: 0, headingDeg: 96, gimbalPitchDeg: -28, distanceFeet: 0 },
        { lat: 39.7401, lng: -104.98895, altitudeFeet: 280, curveFeet: 18, headingDeg: 118, gimbalPitchDeg: -29, distanceFeet: 20 },
        { lat: 39.74035, lng: -104.9886, altitudeFeet: 320, curveFeet: 22, headingDeg: 140, gimbalPitchDeg: -30, distanceFeet: 40 },
        { lat: 39.7407, lng: -104.9881, altitudeFeet: 360, curveFeet: 0, headingDeg: 162, gimbalPitchDeg: -31, distanceFeet: 60 },
      ],
    },
  ],
  batterySummaries: [
    {
      batteryIndex: 1,
      pathDistanceFeet: 540,
      waypointCount: 42,
      captureSpacingFeet: 12,
      maxHeadingGapFeet: 49.72,
      maxHeadingDeltaDeg: 43.31,
      estimatedYawRateDegPerSec: 90,
      captureArcDeg: 180,
      captureIntervalSeconds: 0.5,
      captureTriggerMode: "s",
      captureDistanceFeet: 0,
      stageCount: 2,
      stageWaypointCounts: [99, 44],
      stageAverageSpeedMph: [17.2, 18.6],
    },
    {
      batteryIndex: 2,
      pathDistanceFeet: 610,
      waypointCount: 46,
      captureSpacingFeet: 12,
      maxHeadingGapFeet: 49.72,
      maxHeadingDeltaDeg: 43.31,
      estimatedYawRateDegPerSec: 90,
      captureArcDeg: 180,
      captureIntervalSeconds: 0.5,
      captureTriggerMode: "s",
      captureDistanceFeet: 0,
      stageCount: 1,
      stageWaypointCounts: [78],
      stageAverageSpeedMph: [20.4],
    },
  ],
  overlapTelemetry: {
    captureSpacingFeet: 12,
    captureIntervalSeconds: 0.5,
    captureDistanceFeet: 0,
    captureTriggerMode: "s",
    yawRateDegPerSec: 90,
    captureArcDeg: 180,
  },
};

const exportResponse = {
  batteryIndex: 1,
  telemetry: optimizeResponse.batterySummaries[0],
  previewPath: optimizeResponse.previewPaths[0],
  previewWaypoints: optimizeResponse.previewBatteries[0].waypoints,
  stages: [
    {
      stageNumber: 1,
      filename: "battery-1-part-1.csv",
      waypointCount: 99,
      csvText: "latitude,longitude,altitude(ft),heading(deg)\n39.7392,-104.9903,120,0\n",
    },
    {
      stageNumber: 2,
      filename: "battery-1-part-2.csv",
      waypointCount: 44,
      csvText: "latitude,longitude,altitude(ft),heading(deg)\n39.7398,-104.98955,230,72\n",
    },
  ],
};

test("camera overlap real path mode previews staged exports and preserves straight lab", async ({ page }) => {
  let optimizeRequestCount = 0;
  let exportRequestCount = 0;

  await page.route("**/api/spin-path/optimize", async (route) => {
    optimizeRequestCount += 1;
    const body = route.request().postDataJSON();
    expect(body.center).toBe("39.739200, -104.990300");
    expect(body.overlapConfig.captureSpacingFt).toBeGreaterThan(0);
    expect(body.overlapConfig.captureIntervalUnit).toBe("s");

    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(optimizeResponse),
    });
  });

  await page.route("**/api/spin-path/export/battery/*", async (route) => {
    exportRequestCount += 1;
    const body = route.request().postDataJSON();
    expect(body.overlapConfig.captureSpacingFt).toBeGreaterThan(0);
    expect(body.overlapConfig.captureIntervalUnit).toBe("s");

    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(exportResponse),
    });
  });

  await page.goto("/camera-overlap");

  await expect(page.getByTestId("viewer-3d-path-span")).toBeVisible();
  await expect(page.getByTestId("camera-overlap-page-label")).toContainText("75°×55° FOV");

  await page.getByTestId("workflow-real-path-btn").click();
  await expect(page.getByTestId("real-path-planner")).toBeVisible();

  await page.getByTestId("real-path-center-input").fill("39.739200, -104.990300");
  await page.getByTestId("real-path-battery-minutes").fill("20");
  await page.getByTestId("real-path-battery-count").fill("2");
  await page.getByTestId("real-path-generate-btn").click();

  const mapWrapper = page.locator(".map-wrapper");
  await expect(mapWrapper).toHaveAttribute("data-selected-battery", "1");
  await expect(mapWrapper).toHaveAttribute("data-elevated-line-count", "2");
  await expect(mapWrapper).toHaveAttribute("data-rendered-path-point-count", "4");
  await expect(page.getByText("0.50 s trigger").first()).toBeVisible();
  await expect(page.getByText("Reduced bounces from 8 to 6 to fit battery target")).toBeVisible();

  const downloadPromise = page.waitForEvent("download");
  await page.getByTestId("real-path-download-battery-1").click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toContain("battery-1");

  await expect(page.getByTestId("real-path-export-note")).toContainText("Downloaded battery 1 with 2 stages.");
  expect(optimizeRequestCount).toBe(1);
  expect(exportRequestCount).toBe(1);

  await page.getByTestId("workflow-straight-btn").click();
  await expect(page.getByTestId("viewer-3d-path-span")).toBeVisible();
  await expect(page.getByTestId("camera-overlap-page-label")).toContainText("75°×55° FOV");
});
