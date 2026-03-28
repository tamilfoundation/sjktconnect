import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/api/", "/dashboard/", "/claim/verify/"],
    },
    sitemap: "https://tamilschool.org/sitemap.xml",
  };
}
