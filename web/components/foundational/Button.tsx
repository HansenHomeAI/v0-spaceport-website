import type { ElementType, HTMLAttributes } from 'react';
import Link from 'next/link';
import { cx, toArray } from './utils';

export type ButtonBaseProps = HTMLAttributes<HTMLElement> & {
  as?: ElementType;
  href?: string;
  target?: string;
  rel?: string;
  type?: 'button' | 'submit' | 'reset';
  variant?: string | string[];
  withSymbol?: boolean;
  disabled?: boolean;
};

const isInternalLink = (href?: string) => !!href && href.startsWith('/') && !href.startsWith('//');

export const ButtonBase = ({
  as,
  href,
  target,
  rel,
  type,
  variant,
  withSymbol,
  className,
  ...rest
}: ButtonBaseProps) => {
  const classes = cx(...toArray(variant), withSymbol ? 'with-symbol' : undefined, className);

  if (href) {
    if (isInternalLink(href)) {
      return (
        <Link href={href} className={classes} target={target} rel={rel} {...rest} />
      );
    }

    return (
      <a href={href} className={classes} target={target} rel={rel} {...rest} />
    );
  }

  const Component = as || 'button';
  return <Component className={classes} type={type} {...rest} />;
};

export type ButtonVariantProps = Omit<ButtonBaseProps, 'variant'> & {
  fixed?: boolean;
};

export const Primary = (props: ButtonBaseProps) => (
  <ButtonBase variant="cta-button" {...props} />
);

export const Secondary = ({ fixed, ...props }: ButtonVariantProps) => (
  <ButtonBase variant={fixed ? 'cta-button2-fixed' : 'cta-button2'} {...props} />
);

export const Ghost = (props: ButtonBaseProps) => (
  <ButtonBase variant="cta-button2-fixed" {...props} />
);

export const LinkButton = (props: ButtonBaseProps) => (
  <ButtonBase variant="terms-link" {...props} />
);

export const Button = {
  Base: ButtonBase,
  Primary,
  Secondary,
  Ghost,
  Link: LinkButton,
};

export default Button;
