export type ExifPoint = {
  id: string;
  fileAbs: string;
  fileRel: string;
  fileName: string;
  mime?: string;
  dateTimeOriginal?: string;
  lat?: number;
  lon?: number;
  alt?: number;
  x?: number;
  y?: number;
  gimbalYaw?: number;
  gimbalPitch?: number;
  gimbalRoll?: number;
  cameraYaw?: number;
  cameraPitch?: number;
  cameraRoll?: number;
};

export type ExifIndex = {
  createdAt: string;
  source: {
    zipPath?: string;
    extractedDir: string;
  };
  origin: {
    lat0: number;
    lon0: number;
  };
  points: ExifPoint[];
};

