import type { CSSProperties, ElementType, ComponentPropsWithoutRef } from 'react';
import legacyStyles from './legacy.module.css';
import { cx, mapTokens, toArray, toTokens } from './utils';

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
  const variantClasses = mapTokens(legacyStyles, toArray(variant));
  const classTokens = mapTokens(legacyStyles, toTokens(className));
  return (
    <Component
      className={cx(...variantClasses, ...classTokens)}
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
  const variantClasses = mapTokens(legacyStyles, toArray(variant));
  const classTokens = mapTokens(legacyStyles, toTokens(className));
  return (
    <Component
      className={cx(...variantClasses, ...classTokens)}
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
