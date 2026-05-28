export type LitchiMissionNameInput = {
  projectTitle?: string | null;
  batteryIndex: number;
  totalBatteries: number;
  batchDate?: Date;
};

const MAX_MISSION_NAME_LENGTH = 64;
const DEFAULT_SLUG = 'spaceport-project';

export function sanitizeMissionTitle(projectTitle?: string | null): string {
  const normalized = (projectTitle || '')
    .trim()
    .replace(/\.[a-z0-9]+$/i, '')
    .replace(/[^a-zA-Z0-9 _-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  return normalized || 'Untitled';
}

export function sanitizeMissionSlug(projectTitle?: string | null): string {
  const normalized = (projectTitle || '')
    .trim()
    .replace(/\.[a-z0-9]+$/i, '')
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .replace(/-{2,}/g, '-');

  return normalized || DEFAULT_SLUG;
}

export function formatLitchiBatchId(date: Date = new Date()): string {
  const year = date.getFullYear();
  const month = `${date.getMonth() + 1}`.padStart(2, '0');
  const day = `${date.getDate()}`.padStart(2, '0');
  const hours = `${date.getHours()}`.padStart(2, '0');
  const minutes = `${date.getMinutes()}`.padStart(2, '0');
  const seconds = `${date.getSeconds()}`.padStart(2, '0');
  return `${year}${month}${day}-${hours}${minutes}${seconds}`;
}

export function buildLitchiMissionName({
  projectTitle,
  batteryIndex,
  totalBatteries,
  batchDate = new Date(),
}: LitchiMissionNameInput): string {
  const safeBatteryIndex = Math.max(1, Math.floor(batteryIndex || 1));
  const safeTotal = Math.max(safeBatteryIndex, Math.floor(totalBatteries || safeBatteryIndex));
  const batteryWidth = Math.max(2, `${safeTotal}`.length);
  const flightLabel = `flight-${`${safeBatteryIndex}`.padStart(batteryWidth, '0')}-of-${`${safeTotal}`.padStart(batteryWidth, '0')}`;
  const suffix = `${flightLabel}_${formatLitchiBatchId(batchDate)}`;
  const maxSlugLength = Math.max(12, MAX_MISSION_NAME_LENGTH - suffix.length - 1);
  const slug = sanitizeMissionSlug(projectTitle).slice(0, maxSlugLength).replace(/-+$/g, '');

  return `${slug || DEFAULT_SLUG}_${suffix}`;
}
