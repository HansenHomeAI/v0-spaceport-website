import type { InputHTMLAttributes, TextareaHTMLAttributes } from 'react';
import legacyStyles from './legacy.module.css';
import { cx, mapTokens, toArray, toTokens } from './utils';

export type InputBaseProps = {
  variant?: string | string[];
  className?: string;
};

export type TextInputProps = InputHTMLAttributes<HTMLInputElement> & InputBaseProps;
export type TextAreaProps = TextareaHTMLAttributes<HTMLTextAreaElement> & InputBaseProps;

export const Text = ({ variant, className, ...rest }: TextInputProps) => {
  const variantClasses = mapTokens(legacyStyles, toArray(variant));
  const classTokens = mapTokens(legacyStyles, toTokens(className));
  return <input className={cx(...variantClasses, ...classTokens)} {...rest} />;
};

export const TextArea = ({ variant, className, ...rest }: TextAreaProps) => {
  const variantClasses = mapTokens(legacyStyles, toArray(variant));
  const classTokens = mapTokens(legacyStyles, toTokens(className));
  return <textarea className={cx(...variantClasses, ...classTokens)} {...rest} />;
};

export const Input = { Text, TextArea };
export default Input;
