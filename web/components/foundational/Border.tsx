import type { CSSProperties, ElementType, ComponentPropsWithoutRef } from 'react';
import { cx } from './utils';

export const MIN_RADIUS = 25;

const parsePx = (value: string): number | null => {
  const trimmed = value.trim();
  if (/^-?\d*\.?\d+$/.test(trimmed)) {
    return Number.parseFloat(trimmed);
  }
  const match = trimmed.match(/^(-?\d*\.?\d+)px$/);
  if (match) {
    return Number.parseFloat(match[1]);
  }
  return null;
};

export const resolveRadius = (value?: number | string): string | undefined => {
  if (value === undefined) return undefined;
  if (typeof value === 'number') {
    return `${Math.max(value, MIN_RADIUS)}px`;
  }

  const parsed = parsePx(value);
  if (parsed === null) {
    return value;
  }

  return `${Math.max(parsed, MIN_RADIUS)}px`;
};

export const getConcentricRadius = (inner: number) => {
  const safeInner = Math.max(inner, MIN_RADIUS);
  return {
    inner: safeInner,
    middle: safeInner + 8,
    outer: safeInner + 16,
  };
};

type BorderOwnProps = {
  as?: ElementType;
  radius?: number | string;
  width?: number | string;
  borderStyle?: CSSProperties['borderStyle'];
  color?: CSSProperties['borderColor'];
};

export type BorderProps<T extends ElementType = 'div'> = BorderOwnProps &
  Omit<ComponentPropsWithoutRef<T>, keyof BorderOwnProps>;

export const Border = <T extends ElementType = 'div'>({
  as,
  radius,
  width,
  borderStyle,
  color,
  className,
  style,
  ...rest
}: BorderProps<T>) => {
  const Component = as || 'div';
  const resolvedRadius = resolveRadius(radius);
  const resolvedStyle: CSSProperties = {
    ...style,
    ...(resolvedRadius ? { borderRadius: resolvedRadius } : null),
    ...(width !== undefined ? { borderWidth: width } : null),
    ...(borderStyle ? { borderStyle } : null),
    ...(color ? { borderColor: color } : null),
  };

  return <Component className={cx(className)} style={resolvedStyle} {...rest} />;
};

export default Border;
