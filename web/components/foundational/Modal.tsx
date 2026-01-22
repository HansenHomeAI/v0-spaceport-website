import type { ElementType, ComponentPropsWithoutRef } from 'react';
import legacyStyles from './legacy.module.css';
import { cx, mapTokens, toArray, toTokens } from './utils';

type ModalOwnProps = {
  as?: ElementType;
  variant?: string | string[];
};

export type ModalProps<T extends ElementType = 'div'> = ModalOwnProps &
  Omit<ComponentPropsWithoutRef<T>, keyof ModalOwnProps>;

export const Overlay = <T extends ElementType = 'div'>({
  as,
  variant,
  className,
  ...rest
}: ModalProps<T>) => {
  const Component = as || 'div';
  const variantClasses = mapTokens(legacyStyles, toArray(variant));
  const classTokens = mapTokens(legacyStyles, toTokens(className));
  return <Component className={cx(...variantClasses, ...classTokens)} {...rest} />;
};

export const Content = <T extends ElementType = 'div'>({
  as,
  variant,
  className,
  ...rest
}: ModalProps<T>) => {
  const Component = as || 'div';
  const variantClasses = mapTokens(legacyStyles, toArray(variant));
  const classTokens = mapTokens(legacyStyles, toTokens(className));
  return <Component className={cx(...variantClasses, ...classTokens)} {...rest} />;
};

export const Modal = { Overlay, Content };
export default Modal;
