import type { CSSProperties, ElementType, ComponentPropsWithoutRef } from 'react';
import { cx, toArray } from './utils';
import { resolveRadius } from './Border';

type ContainerOwnProps = {
  as?: ElementType;
  variant?: string | string[];
  padding?: CSSProperties['padding'];
  borderRadius?: number | string;
  background?: CSSProperties['background'];
  backdropFilter?: CSSProperties['backdropFilter'];
  border?: CSSProperties['border'];
  maxWidth?: CSSProperties['maxWidth'];
};

export type ContainerProps<T extends ElementType = 'div'> = ContainerOwnProps &
  Omit<ComponentPropsWithoutRef<T>, keyof ContainerOwnProps>;

export const Container = <T extends ElementType = 'div'>({
  as,
  variant,
  padding,
  borderRadius,
  background,
  backdropFilter,
  border,
  maxWidth,
  className,
  style,
  ...rest
}: ContainerProps<T>) => {
  const Component = as || 'div';
  const classes = cx(...toArray(variant), className);
  const resolvedRadius = resolveRadius(borderRadius);
  const mergedStyle: CSSProperties = {
    ...style,
    ...(padding !== undefined ? { padding } : null),
    ...(resolvedRadius ? { borderRadius: resolvedRadius } : null),
    ...(background ? { background } : null),
    ...(backdropFilter ? { backdropFilter } : null),
    ...(border ? { border } : null),
    ...(maxWidth ? { maxWidth } : null),
  };

  return <Component className={classes} style={mergedStyle} {...rest} />;
};

export default Container;
