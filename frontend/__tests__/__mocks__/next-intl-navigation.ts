const React = require("react");

function createNavigation() {
  function Link({ children, href, ...props }: any) {
    return React.createElement("a", { href, ...props }, children);
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

  return { Link, usePathname, useRouter, redirect };
}

module.exports = { createNavigation };
