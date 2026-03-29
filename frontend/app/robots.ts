import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "AhrefsBot",
        disallow: "/",
      },
      {
        userAgent: "GPTBot",
        disallow: "/",
      },
      {
        userAgent: "OAI-SearchBot",
        disallow: "/",
      },
      {
        userAgent: "Amazonbot",
        disallow: "/",
      },
      {
        userAgent: "ClaudeBot",
        disallow: "/",
      },
      {
        userAgent: "*",
        allow: "/",
        disallow: ["/api/", "/dashboard/", "/claim/verify/"],
      },
    ],
    sitemap: "https://tamilschool.org/sitemap.xml",
  };
}
