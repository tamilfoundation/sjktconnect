// Shim for Next.js 16 auto-generated type validator
// (.next/types/validator.ts references `React.ComponentType` unqualified).
// Until Next 16 fixes its generator, expose the React namespace globally.
import type * as ReactModule from "react";

declare global {
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace React {
    type ComponentType<P = {}> = ReactModule.ComponentType<P>;
    type ReactNode = ReactModule.ReactNode;
    type FC<P = {}> = ReactModule.FC<P>;
  }
}

export {};
