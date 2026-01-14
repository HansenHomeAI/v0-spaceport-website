import type { InputHTMLAttributes, TextareaHTMLAttributes } from 'react';
import { cx, toArray } from './utils';

export type InputBaseProps = {
  variant?: string | string[];
  className?: string;
};

export type TextInputProps = InputHTMLAttributes<HTMLInputElement> & InputBaseProps;
export type TextAreaProps = TextareaHTMLAttributes<HTMLTextAreaElement> & InputBaseProps;

export const Text = ({ variant, className, ...rest }: TextInputProps) => (
  <input className={cx(...toArray(variant), className)} {...rest} />
);

export const TextArea = ({ variant, className, ...rest }: TextAreaProps) => (
  <textarea className={cx(...toArray(variant), className)} {...rest} />
);

export const Input = { Text, TextArea };
export default Input;
