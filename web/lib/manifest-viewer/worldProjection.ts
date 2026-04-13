import * as THREE from "three";
import type { CameraPose, V3 } from "./types";

export function createOverlayPerspectiveCamera(): THREE.PerspectiveCamera {
  return new THREE.PerspectiveCamera(60, 1, 0.05, 5000);
}

export function syncOverlayCamera(
  cam: THREE.PerspectiveCamera,
  pose: CameraPose,
  width: number,
  height: number,
): void {
  const aspect = width > 0 && height > 0 ? width / height : 1;
  cam.fov = pose.fov;
  cam.aspect = aspect;
  cam.position.set(pose.position.x, pose.position.y, pose.position.z);
  cam.lookAt(pose.target.x, pose.target.y, pose.target.z);
  cam.updateProjectionMatrix();
}

export function projectWorldToScreen(
  world: V3,
  cam: THREE.PerspectiveCamera,
  width: number,
  height: number,
): { x: number; y: number; visible: boolean } {
  const v = new THREE.Vector3(world.x, world.y, world.z);
  v.project(cam);
  const x = (v.x * 0.5 + 0.5) * width;
  const y = (-v.y * 0.5 + 0.5) * height;
  const visible = Math.abs(v.x) <= 1.1 && Math.abs(v.y) <= 1.1 && v.z > -1 && v.z < 1;
  return { x, y, visible };
}
