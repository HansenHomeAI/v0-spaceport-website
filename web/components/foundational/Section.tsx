import type { ElementType, ComponentPropsWithoutRef } from 'react';
import { cx, toArray } from './utils';

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
  const classes = cx(
    withBase ? 'section' : undefined,
    ...toArray(variant),
    className
  );

  return <Component className={classes} {...rest} />;
};

export default Section;
