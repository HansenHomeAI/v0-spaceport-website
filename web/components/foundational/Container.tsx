import { forwardRef } from 'react';
import type { CSSProperties, ElementType, ComponentPropsWithRef } from 'react';
import { cx, toArray } from './utils';
import { resolveRadius } from './Border';

type ContainerBaseProps<T extends ElementType> = {
  as?: T;
  variant?: string | string[];
  padding?: CSSProperties['padding'];
  borderRadius?: number | string;
  background?: CSSProperties['background'];
  backdropFilter?: CSSProperties['backdropFilter'];
  border?: CSSProperties['border'];
  maxWidth?: CSSProperties['maxWidth'];
};

export type ContainerProps<T extends ElementType = 'div'> = ContainerBaseProps<T> &
  Omit<ComponentPropsWithRef<T>, keyof ContainerBaseProps<T>>;

type ContainerComponent = <T extends ElementType = 'div'>(
  props: ContainerProps<T> & { ref?: ComponentPropsWithRef<T>['ref'] }
) => JSX.Element;

export const Container = forwardRef(
  <T extends ElementType = 'div'>(
    {
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
    }: ContainerProps<T>,
    ref: ComponentPropsWithRef<T>['ref']
  ) => {
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

    return <Component ref={ref} className={classes} style={mergedStyle} {...rest} />;
  }
) as ContainerComponent;

export default Container;
