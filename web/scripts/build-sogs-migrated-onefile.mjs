import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const webRoot = path.resolve(__dirname, "..");
const repoRoot = path.resolve(webRoot, "..");

const onefileEntry = path.join(webRoot, "standalone", "sogs-migrated-viewer-onefile", "index.tsx");
const outDir = path.join(repoRoot, "exports", "sogs-migrated-viewer-onefile");
const onefileJsPath = path.join(outDir, "index.inline.js");
const onefileCssPath = path.join(outDir, "index.inline.css");
const onefileCssMapPath = path.join(outDir, "index.inline.css.map");
const outHtmlPath = path.join(outDir, "index.html");

const supersplatHtmlPath = path.join(webRoot, "public", "supersplat-viewer", "index.html");
const supersplatCssPath = path.join(webRoot, "public", "supersplat-viewer", "index.css");
const supersplatJsPath = path.join(webRoot, "public", "supersplat-viewer", "index.js");
const bridgePath = path.join(webRoot, "public", "supersplat-viewer", "sogs-bridge.mjs");
const settingsPath = path.join(webRoot, "public", "supersplat-viewer", "settings.json");
const appCssPath = path.join(webRoot, "public", "sogs-migrated-viewer", "index.css");

await fs.mkdir(outDir, { recursive: true });

await build({
  entryPoints: [onefileEntry],
  bundle: true,
  define: {
    "process.env.NODE_ENV": JSON.stringify(process.env.NODE_ENV ?? "production"),
  },
  format: "iife",
  globalName: "SogsMigratedViewerOnefileApp",
  jsx: "automatic",
  legalComments: "none",
  logLevel: "info",
  outfile: onefileJsPath,
  platform: "browser",
  sourcemap: false,
  target: ["es2022"],
});

const [
  appJs,
  appCss,
  supersplatHtml,
  supersplatCss,
  supersplatJs,
  bridgeModule,
  settingsJson,
] = await Promise.all([
  fs.readFile(onefileJsPath, "utf8"),
  fs.readFile(appCssPath, "utf8"),
  fs.readFile(supersplatHtmlPath, "utf8"),
  fs.readFile(supersplatCssPath, "utf8"),
  fs.readFile(supersplatJsPath, "utf8"),
  fs.readFile(bridgePath, "utf8"),
  fs.readFile(settingsPath, "utf8"),
]);

const supersplatBodyMatch = supersplatHtml.match(/<body>([\s\S]*?)<\/body>/i);
if (!supersplatBodyMatch) {
  throw new Error("Could not extract supersplat viewer <body>.");
}

const supersplatBody = supersplatBodyMatch[1]
  .replace(
    /\s*<!--\s*Application Script[\s\S]*?<script[^>]+src=["']\.\/sogs-bridge\.mjs["'][^>]*><\/script>\s*/i,
    "\n",
  )
  .trim();
const supersplatRuntime = supersplatJs
  .replace(/\nexport\s*\{\s*main\s*\};?\s*$/m, "\n")
  .replace(/\n\/\/# sourceMappingURL=.*$/m, "\n");
const bridgeRuntime = bridgeModule
  .replace(/^import\s+\{\s*main\s*\}\s+from\s+"\.\/index\.js";\s*/m, "")
  .replace(
    /^import\s+\{[\s\S]*?\}\s+from\s+"https:\/\/esm\.sh\/playcanvas@2\.13\.2";\s*/m,
    "",
  );

const srcDoc = String.raw`<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover" />
    <title>SuperSplat Viewer</title>
    <style>${supersplatCss}</style>
    <script>
      (() => {
        const frameEl = window.frameElement;
        const createImage = (url) => {
          const img = new Image();
          img.src = url;
          return img;
        };
        const resolveBundleSkyboxUrl = async (contentUrl, explicitSkyboxUrl) => {
          if (explicitSkyboxUrl) {
            return explicitSkyboxUrl;
          }
          try {
            const content = new URL(contentUrl, location.href);
            const bundleUrl = new URL("spaceport_bundle.json", content);
            const response = await fetch(bundleUrl.toString());
            if (!response.ok) {
              return null;
            }
            const bundle = await response.json();
            const skyboxPath = bundle?.skybox?.path;
            return typeof skyboxPath === "string" && skyboxPath.length
              ? new URL(skyboxPath, bundleUrl).toString()
              : null;
          } catch {
            return null;
          }
        };
        const url = new URL(location.href);
        const contentUrl =
          frameEl?.dataset?.sogsContentUrl ||
          (url.searchParams.has("content") ? url.searchParams.get("content") : "./scene.compressed.ply");
        const explicitSkyboxUrl = url.searchParams.get("skybox");
        const posterUrl = url.searchParams.get("poster");
        const inlineSettings = ${settingsJson};
        const configReady = (async () => ({
          poster: posterUrl && createImage(posterUrl),
          skyboxUrl: await resolveBundleSkyboxUrl(contentUrl, explicitSkyboxUrl),
          contentUrl,
          contents: fetch(contentUrl),
          noui: url.searchParams.has("noui"),
          noanim: url.searchParams.has("noanim"),
          ministats: url.searchParams.has("ministats"),
          unified: url.searchParams.has("unified"),
          aa: url.searchParams.has("aa"),
        }))();
        window.sse = {
          configReady,
          settings: Promise.resolve(inlineSettings),
        };
      })();
    </script>
  </head>
  <body>
${supersplatBody}
    <script type="module">
${supersplatRuntime}
${bridgeRuntime}
    </script>
  </body>
</html>`;

const onefileHtml = `<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover" />
    <title>sogs-migrated-viewer</title>
    <meta name="description" content="Canyon-Vista UI with SOGS / SuperSplat viewer" />
    <style>
      html,
      body,
      #root {
        margin: 0;
        width: 100%;
        min-height: 100%;
        background: #000;
      }

      body {
        overflow: hidden;
      }

      #root {
        min-height: 100vh;
      }
    </style>
    <style>${appCss}</style>
  </head>
  <body>
    <div id="root"></div>
    <textarea id="sogs-onefile-viewer-srcdoc" hidden>${srcDoc}</textarea>
    <script>
      const srcDocTextarea = document.getElementById("sogs-onefile-viewer-srcdoc");
      window.__SOGS_ONEFILE_VIEWER_SRCDOC__ = srcDocTextarea ? srcDocTextarea.value : "";
    </script>
    <script>${appJs}</script>
  </body>
</html>`;

await fs.writeFile(outHtmlPath, onefileHtml);
await fs.rm(onefileJsPath, { force: true });
await fs.rm(onefileCssPath, { force: true });
await fs.rm(onefileCssMapPath, { force: true });
