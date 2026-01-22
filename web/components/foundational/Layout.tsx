import type { CSSProperties, ElementType, ComponentPropsWithoutRef } from 'react';
import legacyStyles from './legacy.module.css';
import { cx, mapTokens, toArray, toTokens } from './utils';

type LayoutOwnProps = {
  as?: ElementType;
  variant?: string | string[];
  gap?: CSSProperties['gap'];
  align?: CSSProperties['alignItems'];
  justify?: CSSProperties['justifyContent'];
  direction?: CSSProperties['flexDirection'];
  wrap?: CSSProperties['flexWrap'];
  columns?: CSSProperties['gridTemplateColumns'];
};

export type LayoutProps<T extends ElementType = 'div'> = LayoutOwnProps &
  Omit<ComponentPropsWithoutRef<T>, keyof LayoutOwnProps>;

const buildClassName = (variant: string | string[] | undefined, className?: string) => {
  const variantClasses = mapTokens(legacyStyles, toArray(variant));
  const classTokens = mapTokens(legacyStyles, toTokens(className));
  return cx(...variantClasses, ...classTokens);
};

export const Flex = <T extends ElementType = 'div'>({
  as,
  variant,
  gap,
  align,
  justify,
  direction,
  wrap,
  className,
  style,
  ...rest
}: LayoutProps<T>) => {
  const Component = as || 'div';
  const mergedStyle: CSSProperties = {
    display: 'flex',
    ...style,
    ...(gap !== undefined ? { gap } : null),
    ...(align ? { alignItems: align } : null),
    ...(justify ? { justifyContent: justify } : null),
    ...(direction ? { flexDirection: direction } : null),
    ...(wrap ? { flexWrap: wrap } : null),
  };

  return (
    <Component
      className={buildClassName(variant, className)}
      style={mergedStyle}
      {...rest}
    />
  );
};

export const Grid = <T extends ElementType = 'div'>({
  as,
  variant,
  gap,
  align,
  justify,
  columns,
  className,
  style,
  ...rest
}: LayoutProps<T>) => {
  const Component = as || 'div';
  const mergedStyle: CSSProperties = {
    display: 'grid',
    ...style,
    ...(gap !== undefined ? { gap } : null),
    ...(align ? { alignItems: align } : null),
    ...(justify ? { justifyContent: justify } : null),
    ...(columns ? { gridTemplateColumns: columns } : null),
  };

  return (
    <Component
      className={buildClassName(variant, className)}
      style={mergedStyle}
      {...rest}
    />
  );
};

type TwoColOwnProps = {
  as?: ElementType;
  variant?: string | string[];
};

export type TwoColProps<T extends ElementType = 'div'> = TwoColOwnProps &
  Omit<ComponentPropsWithoutRef<T>, keyof TwoColOwnProps>;

export const TwoCol = <T extends ElementType = 'div'>({
  as,
  variant,
  className,
  ...rest
}: TwoColProps<T>) => {
  const Component = as || 'div';
  return (
    <Component
      className={buildClassName(['two-col-content', ...toArray(variant)], className)}
      {...rest}
    />
  );
};

export const Layout = { Flex, Grid, TwoCol };
export default Layout;
