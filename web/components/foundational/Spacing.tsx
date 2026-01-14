import type { CSSProperties, ElementType, ComponentPropsWithoutRef } from 'react';
import { cx, toArray } from './utils';

export type SpacingValue = number | string;

export const space = (value: number): string => `${value * 8}px`;

const resolveSpacing = (value?: SpacingValue): string | undefined => {
  if (value === undefined) return undefined;
  return typeof value === 'number' ? space(value) : value;
};

type SpacingOwnProps = {
  as?: ElementType;
  variant?: string | string[];
  margin?: SpacingValue;
  marginX?: SpacingValue;
  marginY?: SpacingValue;
  padding?: SpacingValue;
  paddingX?: SpacingValue;
  paddingY?: SpacingValue;
};

export type SpacingProps<T extends ElementType = 'div'> = SpacingOwnProps &
  Omit<ComponentPropsWithoutRef<T>, keyof SpacingOwnProps>;

export const Spacing = <T extends ElementType = 'div'>({
  as,
  variant,
  margin,
  marginX,
  marginY,
  padding,
  paddingX,
  paddingY,
  className,
  style,
  ...rest
}: SpacingProps<T>) => {
  const Component = as || 'div';
  const resolvedStyle: CSSProperties = {
    ...style,
    ...(margin !== undefined ? { margin: resolveSpacing(margin) } : null),
    ...(marginX !== undefined
      ? { marginLeft: resolveSpacing(marginX), marginRight: resolveSpacing(marginX) }
      : null),
    ...(marginY !== undefined
      ? { marginTop: resolveSpacing(marginY), marginBottom: resolveSpacing(marginY) }
      : null),
    ...(padding !== undefined ? { padding: resolveSpacing(padding) } : null),
    ...(paddingX !== undefined
      ? { paddingLeft: resolveSpacing(paddingX), paddingRight: resolveSpacing(paddingX) }
      : null),
    ...(paddingY !== undefined
      ? { paddingTop: resolveSpacing(paddingY), paddingBottom: resolveSpacing(paddingY) }
      : null),
  };

  return (
    <Component
      className={cx(...toArray(variant), className)}
      style={resolvedStyle}
      {...rest}
    />
  );
};

export default Spacing;
