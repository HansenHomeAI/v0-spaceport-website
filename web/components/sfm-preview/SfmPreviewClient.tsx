"use client";

import { useEffect, useMemo, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import * as THREE from "three";
import type { SfmPreviewPageData, SfmPreviewSamplePayload } from "../../lib/sfmPreview";

function formatNumber(value: number | null): string {
  if (value === null || Number.isNaN(value)) {
    return "Unavailable";
  }
  return new Intl.NumberFormat("en-US").format(value);
}

function formatBytes(value: number): string {
  if (!Number.isFinite(value) || value <= 0) {
    return "0 B";
  }

  const units = ["B", "KB", "MB", "GB", "TB"];
  let size = value;
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }

  return `${size.toFixed(size >= 10 || unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function PointCloud({ preview }: { preview: SfmPreviewSamplePayload }) {
  const geometry = useMemo(() => {
    const pointGeometry = new THREE.BufferGeometry();
    pointGeometry.setAttribute(
      "position",
      new THREE.Float32BufferAttribute(preview.positions, 3),
    );
    pointGeometry.setAttribute(
      "color",
      new THREE.Float32BufferAttribute(preview.colors, 3),
    );
    pointGeometry.computeBoundingSphere();
    return pointGeometry;
  }, [preview.colors, preview.positions]);

  useEffect(() => () => geometry.dispose(), [geometry]);

  return (
    <points geometry={geometry}>
      <pointsMaterial size={0.0175} sizeAttenuation vertexColors transparent opacity={0.96} />
    </points>
  );
}

export default function SfmPreviewClient({ pageData }: { pageData: SfmPreviewPageData }) {
  const [preview, setPreview] = useState<SfmPreviewSamplePayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadPreview() {
      try {
        const response = await fetch("/api/sfm-preview", { cache: "no-store" });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload?.error || "Failed to fetch SfM preview data");
        }

        if (!cancelled) {
          setPreview(payload);
        }
      } catch (fetchError) {
        if (!cancelled) {
          setError(fetchError instanceof Error ? fetchError.message : "Failed to fetch SfM preview data");
        }
      }
    }

    loadPreview();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main
      style={{
        minHeight: "100vh",
        background:
          "radial-gradient(circle at top left, rgba(255,109,58,0.16), transparent 28%), linear-gradient(180deg, #09111a 0%, #05080d 100%)",
        color: "#f8fafc",
        padding: "32px 24px 48px",
      }}
    >
      <div style={{ maxWidth: 1320, margin: "0 auto", display: "grid", gap: 24 }}>
        <section
          style={{
            display: "grid",
            gap: 16,
            border: "1px solid rgba(148,163,184,0.18)",
            borderRadius: 28,
            padding: "28px 30px",
            background: "rgba(7, 14, 23, 0.76)",
            boxShadow: "0 24px 70px rgba(0,0,0,0.35)",
          }}
        >
          <div style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "center" }}>
            <span
              style={{
                padding: "7px 11px",
                borderRadius: 999,
                background: "rgba(249,115,22,0.16)",
                color: "#fdba74",
                fontSize: 13,
                letterSpacing: "0.06em",
                textTransform: "uppercase",
              }}
            >
              Verified completed SfM run
            </span>
            <span
              style={{
                padding: "7px 11px",
                borderRadius: 999,
                background: "rgba(34,197,94,0.16)",
                color: "#86efac",
                fontSize: 13,
              }}
            >
              {pageData.artifact.subsetName}
            </span>
          </div>
          <div style={{ display: "grid", gap: 10 }}>
            <h1 style={{ margin: 0, fontSize: "clamp(2rem, 4vw, 3.6rem)", lineHeight: 1.02 }}>
              {pageData.artifact.title}
            </h1>
            <p style={{ margin: 0, maxWidth: 920, color: "#cbd5e1", fontSize: 17, lineHeight: 1.6 }}>
              This page targets the most recent completed 2000-ladder SfM processing job,
              <code style={{ marginLeft: 6 }}>{pageData.artifact.jobName}</code>, and renders a sampled preview from the
              verified COLMAP sparse output while exposing signed links to the underlying S3 artifacts.
            </p>
          </div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
              gap: 12,
            }}
          >
            {[
              ["Sparse points", formatNumber(pageData.exactPointCount)],
              ["Registered images", formatNumber(pageData.registeredImageCount)],
              ["Planner chunks", formatNumber(pageData.chunkCount)],
              ["Created", formatDate(pageData.artifact.createdAt)],
              ["Completed", formatDate(pageData.artifact.completedAt)],
            ].map(([label, value]) => (
              <div
                key={label}
                style={{
                  padding: "14px 16px",
                  borderRadius: 20,
                  border: "1px solid rgba(148,163,184,0.14)",
                  background: "rgba(15, 23, 42, 0.62)",
                }}
              >
                <div style={{ color: "#94a3b8", fontSize: 13 }}>{label}</div>
                <div style={{ marginTop: 6, fontSize: 20, fontWeight: 600 }}>{value}</div>
              </div>
            ))}
          </div>
          <div style={{ display: "grid", gap: 8, color: "#94a3b8", fontSize: 14 }}>
            <div>
              <strong style={{ color: "#e2e8f0" }}>Output S3 URI:</strong>{" "}
              <code>{pageData.artifact.outputS3Uri}</code>
            </div>
            <div>
              <strong style={{ color: "#e2e8f0" }}>Source ZIP:</strong>{" "}
              <code>{pageData.artifact.sourceZipS3Uri}</code>
            </div>
            <div>
              <strong style={{ color: "#e2e8f0" }}>Planner:</strong> {pageData.planner || "Unavailable"} with signed
              object links that expire in about {Math.round(pageData.linkExpirySeconds / 3600)} hours.
            </div>
          </div>
        </section>

        <section
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(0, 1.9fr) minmax(320px, 1fr)",
            gap: 20,
          }}
        >
          <div
            style={{
              borderRadius: 28,
              border: "1px solid rgba(148,163,184,0.16)",
              background: "rgba(6, 12, 18, 0.82)",
              minHeight: 640,
              overflow: "hidden",
              boxShadow: "0 24px 70px rgba(0,0,0,0.28)",
            }}
          >
            {preview ? (
              <Canvas camera={{ position: [1.7, 1.25, 1.95], near: 0.01, far: 50 }}>
                <color attach="background" args={["#05080d"]} />
                <ambientLight intensity={0.4} />
                <directionalLight position={[3, 4, 2]} intensity={1.15} />
                <gridHelper args={[4, 12, "#334155", "#18212f"]} />
                <axesHelper args={[1.2]} />
                <PointCloud preview={preview} />
                <OrbitControls enableDamping dampingFactor={0.08} />
              </Canvas>
            ) : (
              <div
                style={{
                  minHeight: 640,
                  display: "grid",
                  placeItems: "center",
                  padding: 24,
                  color: error ? "#fca5a5" : "#cbd5e1",
                  textAlign: "center",
                }}
              >
                <div style={{ display: "grid", gap: 10 }}>
                  <strong style={{ fontSize: 18 }}>
                    {error ? "Preview sampling failed" : "Sampling the verified sparse cloud"}
                  </strong>
                  <span style={{ maxWidth: 540, lineHeight: 1.6 }}>
                    {error ||
                      "The local API is reading evenly spaced byte ranges from points3D.txt and generating a lightweight point cloud preview for this page."}
                  </span>
                </div>
              </div>
            )}
          </div>

          <aside
            style={{
              display: "grid",
              gap: 16,
              alignContent: "start",
            }}
          >
            <div
              style={{
                borderRadius: 24,
                border: "1px solid rgba(148,163,184,0.16)",
                background: "rgba(10, 17, 27, 0.86)",
                padding: 22,
                display: "grid",
                gap: 10,
              }}
            >
              <h2 style={{ margin: 0, fontSize: 20 }}>Preview sample</h2>
              <p style={{ margin: 0, color: "#94a3b8", lineHeight: 1.6 }}>
                The canvas uses a normalized sample from the real sparse reconstruction so you can verify geometry
                immediately without downloading the full 201 MB point file in the browser.
              </p>
              <div style={{ display: "grid", gap: 8, color: "#e2e8f0", fontSize: 14 }}>
                <div>Sampled points: {formatNumber(preview?.sampledPointCount ?? null)}</div>
                <div>Sampled ranges: {formatNumber(preview?.sampledRanges ?? null)}</div>
                <div>Source object size: {preview ? formatBytes(preview.sourceSizeBytes) : "Loading…"}</div>
                <div>Per-range window: {preview ? formatBytes(preview.sampleWindowBytes) : "Loading…"}</div>
              </div>
            </div>

            <div
              style={{
                borderRadius: 24,
                border: "1px solid rgba(148,163,184,0.16)",
                background: "rgba(10, 17, 27, 0.86)",
                padding: 22,
                display: "grid",
                gap: 14,
              }}
            >
              <h2 style={{ margin: 0, fontSize: 20 }}>Verified artifact links</h2>
              {pageData.links.map((link) => (
                <a
                  key={link.key}
                  href={link.signedUrl}
                  target="_blank"
                  rel="noreferrer"
                  style={{
                    display: "grid",
                    gap: 6,
                    textDecoration: "none",
                    color: "#f8fafc",
                    padding: "14px 16px",
                    borderRadius: 18,
                    background: "rgba(15, 23, 42, 0.7)",
                    border: "1px solid rgba(148,163,184,0.14)",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                    <strong>{link.label}</strong>
                    <span style={{ color: link.verified ? "#86efac" : "#fda4af", fontSize: 13 }}>
                      {link.verified ? "Verified" : "Unavailable"}
                    </span>
                  </div>
                  <span style={{ color: "#cbd5e1", fontSize: 13 }}>{formatBytes(link.sizeBytes)}</span>
                  <code
                    style={{
                      color: "#94a3b8",
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {link.s3Uri}
                  </code>
                </a>
              ))}
            </div>
          </aside>
        </section>
      </div>
    </main>
  );
}
