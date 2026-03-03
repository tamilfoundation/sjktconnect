import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import AboutPage from "@/app/[locale]/about/page";

// Mock next-intl/server
jest.mock("next-intl/server", () => ({
  getTranslations: jest.fn((namespace: string) => {
    const messages = require("@/messages/en.json");
    const ns = messages[namespace] || {};
    return Promise.resolve((key: string) => ns[key] || key);
  }),
}));

describe("About Page", () => {
  it("renders the page title", async () => {
    const Page = await AboutPage();
    render(Page);
    expect(screen.getByText("About SJK(T) Connect")).toBeInTheDocument();
  });

  it("renders What We Do section", async () => {
    const Page = await AboutPage();
    render(Page);
    expect(screen.getByText("What We Do")).toBeInTheDocument();
  });

  it("renders three feature cards", async () => {
    const Page = await AboutPage();
    render(Page);
    expect(screen.getByText("Parliament Watch")).toBeInTheDocument();
    expect(screen.getByText("News Watch")).toBeInTheDocument();
    expect(screen.getByText("School Directory")).toBeInTheDocument();
  });

  it("renders Tamil Foundation section", async () => {
    const Page = await AboutPage();
    render(Page);
    expect(
      screen.getByText("About Tamil Foundation Malaysia")
    ).toBeInTheDocument();
  });

  it("renders contact email", async () => {
    const Page = await AboutPage();
    render(Page);
    expect(screen.getByText("info@tamilfoundation.org")).toBeInTheDocument();
  });

  it("renders data sources section", async () => {
    const Page = await AboutPage();
    render(Page);
    expect(screen.getByText("Data Sources")).toBeInTheDocument();
  });
});
