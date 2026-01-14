export type ClassValue = string | false | null | undefined;

export const cx = (...values: ClassValue[]): string =>
  values.filter(Boolean).join(' ');

export const toArray = (value?: string | string[]): string[] => {
  if (!value) return [];
  return Array.isArray(value) ? value : [value];
};
