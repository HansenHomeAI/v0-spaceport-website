import type { ElementType, ComponentPropsWithoutRef } from 'react';
import { cx, toArray } from './utils';

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
  return <Component className={cx(...toArray(variant), className)} {...rest} />;
};

export const Content = <T extends ElementType = 'div'>({
  as,
  variant,
  className,
  ...rest
}: ModalProps<T>) => {
  const Component = as || 'div';
  return <Component className={cx(...toArray(variant), className)} {...rest} />;
};

export const Modal = { Overlay, Content };
export default Modal;
