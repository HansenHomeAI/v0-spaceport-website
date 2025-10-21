const fs = require('fs');
const path = require('path');

async function copyCesiumAssets() {
  const sourceDir = path.join(__dirname, '..', 'node_modules', 'cesium', 'Build', 'Cesium');
  const targetDir = path.join(__dirname, '..', 'public', 'cesium');

  if (!fs.existsSync(sourceDir)) {
    console.error(`[copy-cesium-assets] Source directory missing: ${sourceDir}`);
    process.exit(1);
  }

  await fs.promises.rm(targetDir, { recursive: true, force: true });
  await fs.promises.mkdir(targetDir, { recursive: true });

  await fs.promises.cp(sourceDir, targetDir, { recursive: true });
  console.log(`[copy-cesium-assets] Copied Cesium assets to ${targetDir}`);
}

copyCesiumAssets().catch(err => {
  console.error('[copy-cesium-assets] Failed', err);
  process.exit(1);
});
