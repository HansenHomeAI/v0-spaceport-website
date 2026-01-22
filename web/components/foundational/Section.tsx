import type { ElementType, ComponentPropsWithoutRef } from 'react';
import legacyStyles from './legacy.module.css';
import { cx, mapTokens, toArray, toTokens } from './utils';

type SectionOwnProps = {
  as?: ElementType;
  variant?: string | string[];
  withBase?: boolean;
};

export type SectionProps<T extends ElementType = 'section'> = SectionOwnProps &
  Omit<ComponentPropsWithoutRef<T>, keyof SectionOwnProps>;

export const Section = <T extends ElementType = 'section'>({
  as,
  variant,
  withBase = true,
  className,
  ...rest
}: SectionProps<T>) => {
  const Component = as || 'section';
  const variantClasses = mapTokens(legacyStyles, toArray(variant));
  const classTokens = mapTokens(legacyStyles, toTokens(className));
  const baseClass = withBase ? legacyStyles.section : undefined;
  const classes = cx(baseClass, ...variantClasses, ...classTokens);

  return <Component className={classes} {...rest} />;
};

export default Section;
