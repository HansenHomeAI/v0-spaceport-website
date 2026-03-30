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
  await expect(page.locator('.splat-editor-transform-field input').nth(0)).toHaveValue("0.03");
  await expect(page.locator('.splat-editor-transform-field input').nth(1)).toHaveValue("0.1");
  await expect(page.locator('.splat-editor-transform-field input').nth(2)).toHaveValue("0.15");
  await expect(page.locator('.splat-editor-transform-field input').nth(3)).toHaveValue("-100");
  await expect(page.locator('.splat-editor-transform-field input').nth(4)).toHaveValue("0");
  await expect(page.locator('.splat-editor-transform-field input').nth(5)).toHaveValue("0");
  const viewerFrame = page.frameLocator('iframe[title="splat-editor-viewer"]');
  await expect(page.locator('iframe[title="splat-editor-viewer"]')).toBeVisible();
  const viewer = page.frames().find((frame) => frame.url().includes("/supersplat-viewer/index.html"));
  expect(viewer).toBeTruthy();
  await expect
    .poll(async () => {
      return viewer!.evaluate(() => {
        const g = window.__sogsCtx?.app?.root?.findByName?.("gsplat");
        if (!g) {
          return null;
        }
        const p = g.getLocalPosition();
        const e = g.getLocalEulerAngles();
        return {
          position: [p.x, p.y, p.z],
          rotation: [e.x, e.y, e.z],
        };
      });
    })
    .toEqual({
      position: [0.03, 0.1, 0.15],
      rotation: [-100, 0, 0],
    });

  await expect
    .poll(
      async () => {
        return viewer!.evaluate(() => {
          const labels = ["X axis", "Y axis", "Z axis"];
          return labels.every((label) => {
            const element = document.querySelector(`button[aria-label="${label}"]`);
            return !!element && getComputedStyle(element).display !== "none";
          });
        });
      },
      { timeout: 30_000 },
    )
    .toBe(true);

  const workingPlyPath = (await page.getByTestId("splat-working-ply-path").textContent())?.trim();
  const originalSessionId = (await page.getByTestId("splat-session-id").textContent())?.trim();
  const firstHash = (await page.getByTestId("splat-revision-hash").textContent())?.trim();
  await expect(page.getByTestId("splat-history-state")).toHaveText("1/1");
  expect(workingPlyPath).toBeTruthy();
  expect(originalSessionId).toBeTruthy();
  expect(firstHash).toBeTruthy();

  execFileSync("node", ["web/scripts/edit-3dgs-ply.mjs", "--input", workingPlyPath!, "--radius-gt", "0.75"], {
    cwd: path.resolve("."),
    stdio: "pipe",
  });

  await expect(page.getByTestId("splat-revision-hash")).not.toHaveText(firstHash!, { timeout: 30_000 });
  const updatedHash = (await page.getByTestId("splat-revision-hash").textContent())?.trim();
  expect(updatedHash).toBeTruthy();
  await expect(page.getByTestId("splat-history-state")).toHaveText("2/2");

  await page.getByRole("button", { name: "Undo" }).click();
  await expect(page.getByTestId("splat-revision-hash")).toHaveText(firstHash!);
  await expect(page.getByTestId("splat-history-state")).toHaveText("1/2");

  await page.getByRole("button", { name: "Redo" }).click();
  await expect(page.getByTestId("splat-revision-hash")).toHaveText(updatedHash!);
  await expect(page.getByTestId("splat-history-state")).toHaveText("2/2");

  await page.reload();
  await expect(page.getByTestId("splat-session-id")).toHaveText(originalSessionId!);
  await expect(page.getByTestId("splat-working-ply-path")).toHaveText(workingPlyPath!);
  await expect(page.getByTestId("splat-revision-hash")).toHaveText(updatedHash!);
  await expect(page.getByTestId("splat-viewer-state")).toHaveText("ready", { timeout: 180_000 });
  await expect(page.getByTestId("splat-history-state")).toHaveText("2/2");

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
