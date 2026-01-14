import type { CSSProperties, ElementType, ComponentPropsWithoutRef } from 'react';
import { cx, toArray } from './utils';

type ColorOwnProps = {
  as?: ElementType;
  variant?: string | string[];
  background?: CSSProperties['background'];
  color?: CSSProperties['color'];
};

export type ColorProps<T extends ElementType = 'div'> = ColorOwnProps &
  Omit<ComponentPropsWithoutRef<T>, keyof ColorOwnProps>;

export const Background = <T extends ElementType = 'div'>({
  as,
  variant,
  background,
  className,
  style,
  ...rest
}: ColorProps<T>) => {
  const Component = as || 'div';
  return (
    <Component
      className={cx(...toArray(variant), className)}
      style={{
        ...style,
        ...(background ? { background } : null),
      }}
      {...rest}
    />
  );
};

export const TextColor = <T extends ElementType = 'span'>({
  as,
  variant,
  color,
  className,
  style,
  ...rest
}: ColorProps<T>) => {
  const Component = as || 'span';
  return (
    <Component
      className={cx(...toArray(variant), className)}
      style={{
        ...style,
        ...(color ? { color } : null),
      }}
      {...rest}
    />
  );
};

export const Color = { Background, Text: TextColor };
export default Color;
