import { test, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";
import os from "node:os";
import path from "node:path";

const REAL_TEST_SOURCE =
  process.env.SPLAT_EDITOR_TEST_SOURCE ??
  "s3://spaceport-ml-processing-staging/manual-validations/staging-colmap-subset-1774554423/3dgs/staging-colmap-subset-1774554423-3dgs/output/model.tar.gz";

test("imports a real 3DGS tarball, auto-refreshes after CLI edit, and exports the same format", async ({ page }) => {
  test.setTimeout(240_000);

  await page.goto("/splat-editor");
  await page.getByTestId("splat-source-input").fill(REAL_TEST_SOURCE);
  await expect(page.getByTestId("splat-import-button")).toBeEnabled();
  await page.getByTestId("splat-import-button").click();

  await expect(page.getByTestId("splat-session-id")).toBeVisible({ timeout: 180_000 });
  await expect(page.getByTestId("splat-artifact-type")).toHaveText("model.tar.gz");
  await expect(page.getByTestId("splat-viewer-state")).toHaveText("ready", { timeout: 180_000 });
  await expect(page.locator('iframe[title="splat-editor-viewer"]')).toBeVisible();

  const workingPlyPath = (await page.getByTestId("splat-working-ply-path").textContent())?.trim();
  const firstHash = (await page.getByTestId("splat-revision-hash").textContent())?.trim();
  expect(workingPlyPath).toBeTruthy();
  expect(firstHash).toBeTruthy();

  execFileSync("node", ["web/scripts/edit-3dgs-ply.mjs", "--input", workingPlyPath!, "--radius-gt", "0.75"], {
    cwd: path.resolve("."),
    stdio: "pipe",
  });

  await expect(page.getByTestId("splat-revision-hash")).not.toHaveText(firstHash!, { timeout: 30_000 });

  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByTestId("splat-export-link").click(),
  ]);

  expect(download.suggestedFilename()).toBe("edited-model.tar.gz");
  const downloadPath = path.join(os.tmpdir(), `splat-editor-${Date.now()}.tar.gz`);
  await download.saveAs(downloadPath);

  const listing = execFileSync("tar", ["-tzf", downloadPath], { encoding: "utf8" });
  expect(listing).toContain("training_metadata.json");
  expect(listing).toContain("splat.ply");
});
