// Ambient declarations providing complete types when node_modules is missing or in isolated environments

declare namespace JSX {
  interface IntrinsicElements {
    [elemName: string]: any;
  }
  interface Element extends React.ReactElement<any, any> {}
}

declare module "react" {
  export type ReactNode = any;
  export type ReactElement<P = any, T extends string | React.JSXElementConstructor<any> = string | React.JSXElementConstructor<any>> = any;
  export type JSXElementConstructor<P> = ((props: P) => ReactElement<any, any> | null) | (new (props: P) => any);
  
  export type Dispatch<A> = (value: A) => void;
  export type SetStateAction<S> = S | ((prevState: S) => S);

  export function useState<T>(initialState: T | (() => T)): [T, Dispatch<SetStateAction<T>>];
  export function useEffect(effect: () => void | (() => void), deps?: readonly any[]): void;
  export function useMemo<T>(factory: () => T, deps: readonly any[] | undefined): T;
  export function useCallback<T extends (...args: any[]) => any>(callback: T, deps: readonly any[]): T;
  export function useRef<T>(initialValue: T): { current: T };

  export interface FormEvent<T = Element> {
    preventDefault(): void;
    stopPropagation(): void;
  }
  export interface ChangeEvent<T = Element> {
    target: T & { value: string; checked?: boolean };
  }
  export interface MouseEvent<T = Element> {
    preventDefault(): void;
    stopPropagation(): void;
  }
  export interface KeyboardEvent<T = Element> {
    key: string;
    preventDefault(): void;
  }

  const React: {
    useState: typeof useState;
    useEffect: typeof useEffect;
    useMemo: typeof useMemo;
    useCallback: typeof useCallback;
    useRef: typeof useRef;
  };
  export default React;
}

declare module "react/jsx-runtime" {
  export const jsx: any;
  export const jsxs: any;
  export const Fragment: any;
}

declare module "react-dom" {
  export const createPortal: any;
}

declare module "next" {
  export interface Metadata {
    title?: string | { default: string; template: string };
    description?: string;
    [key: string]: any;
  }
}

declare module "next/link" {
  import type { ReactNode } from "react";
  export interface LinkProps {
    href: string;
    children?: ReactNode;
    className?: string;
    title?: string;
    target?: string;
    rel?: string;
    role?: string;
    "aria-current"?: string | boolean;
    onClick?: (e: any) => void;
    [key: string]: any;
  }
  const Link: (props: LinkProps) => any;
  export default Link;
}

declare module "tailwindcss" {
  export type Config = any;
  const config: any;
  export default config;
}

declare module "*.css" {
  const content: any;
  export default content;
}

declare const process: {
  env: {
    NEXT_PUBLIC_API_URL?: string;
    [key: string]: string | undefined;
  };
};
