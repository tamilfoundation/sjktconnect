import React from "react";

function Link({ children, href, ...props }: any) {
  return (
    <a href={href} {...props}>
      {children}
    </a>
  );
}

function usePathname() {
  return "/";
}

function useRouter() {
  return {
    push: jest.fn(),
    replace: jest.fn(),
    back: jest.fn(),
  };
}

function redirect(_url: string) {
  // no-op in tests
}

module.exports = { Link, usePathname, useRouter, redirect };
