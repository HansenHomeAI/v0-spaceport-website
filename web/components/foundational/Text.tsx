import type { CSSProperties, HTMLAttributes } from 'react';
import { cx } from './utils';

export type TextAlign = 'left' | 'center' | 'right';

type TextTag = 'h1' | 'h2' | 'h3' | 'p';

export type TextProps = HTMLAttributes<HTMLElement> & {
  align?: TextAlign;
  color?: string;
  marginAll?: string | number;
  margiall?: string | number;
  withBase?: boolean;
};

const buildStyle = (
  style: CSSProperties | undefined,
  align?: TextAlign,
  color?: string,
  marginAll?: string | number,
  margiall?: string | number
): CSSProperties | undefined => {
  const resolvedMargin = marginAll ?? margiall;
  if (!align && !color && resolvedMargin === undefined) {
    return style;
  }

  return {
    ...style,
    ...(align ? { textAlign: align } : null),
    ...(color ? { color } : null),
    ...(resolvedMargin !== undefined ? { margin: resolvedMargin } : null),
  };
};

const createText = (Tag: TextTag, baseClass: string) => {
  const Component = ({
    align,
    color,
    marginAll,
    margiall,
    withBase = true,
    className,
    style,
    ...rest
  }: TextProps) => (
    <Tag
      className={cx(withBase ? baseClass : undefined, className)}
      style={buildStyle(style, align, color, marginAll, margiall)}
      {...rest}
    />
  );

  Component.displayName = `Text.${String(Tag).toUpperCase()}`;
  return Component;
};

const H1 = createText('h1', 'text-h1');
const H2Base = createText('h2', 'text-h2');
const H2 = (props: TextProps) => (
  <H2Base
    {...props}
    style={{
      ...props.style,
      textDecoration: 'underline wavy rgb(255, 0, 0)',
    }}
  />
);
const H3 = createText('h3', 'text-h3');
const Body = createText('p', 'text-body');
const Small = createText('p', 'text-small');
const Emphasis = createText('p', 'text-emphasis');

export const Text = { H1, H2, H3, Body, Small, Emphasis };
export default Text;
