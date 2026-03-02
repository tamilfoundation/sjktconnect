/** @type {import('jest').Config} */
module.exports = {
  testEnvironment: "jsdom",
  transform: {
    "^.+\\.tsx?$": [
      "ts-jest",
      {
        tsconfig: {
          jsx: "react-jsx",
          module: "commonjs",
          esModuleInterop: true,
          moduleResolution: "node",
          paths: { "@/*": ["./*"] },
        },
      },
    ],
  },
  moduleNameMapper: {
    "^@/(.*)$": "<rootDir>/$1",
    "\\.(css|less|scss|sass)$": "<rootDir>/__tests__/__mocks__/styleMock.js",
    "^next-intl$": "<rootDir>/__tests__/__mocks__/next-intl.ts",
    "^next-intl/server$": "<rootDir>/__tests__/__mocks__/next-intl-server.ts",
    "^next-intl/navigation$": "<rootDir>/__tests__/__mocks__/next-intl-navigation.ts",
    "^next-intl/routing$": "<rootDir>/__tests__/__mocks__/next-intl-routing.ts",
    "^@/i18n/navigation$": "<rootDir>/__tests__/__mocks__/i18n-navigation.tsx",
    "^@/i18n/routing$": "<rootDir>/__tests__/__mocks__/i18n-routing.ts",
  },
  testMatch: ["**/__tests__/**/*.test.ts", "**/__tests__/**/*.test.tsx"],
};
