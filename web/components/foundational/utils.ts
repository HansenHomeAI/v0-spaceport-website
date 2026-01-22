export type ClassValue = string | false | null | undefined;

export const cx = (...values: ClassValue[]): string =>
  values.filter(Boolean).join(' ');

export const toArray = (value?: string | string[]): string[] => {
  if (!value) return [];
  return Array.isArray(value) ? value : [value];
};

export const toTokens = (value?: string | string[]): string[] => {
  if (!value) return [];
  const raw = Array.isArray(value) ? value : [value];
  return raw.flatMap((item) => item.split(' ').filter(Boolean));
};

export const mapTokens = (styles: Record<string, string>, tokens: string[]): string[] =>
  tokens.map((token) => styles[token] ?? token);
