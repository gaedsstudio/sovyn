import type { MetadataRoute } from "next";
import { listPackages } from "../lib/registry/registry";

const routes = [
  "/",
  "/hub",
  "/verified",
  "/community",
  "/publish",
  "/developers",
  "/docs",
  "/security",
  "/about",
] as const;

export default function sitemap(): MetadataRoute.Sitemap {
  const base = "https://sovyn.org";
  const staticRoutes = routes.map((route) => ({ url: `${base}${route}` }));
  const packageRoutes = listPackages().map((item) => ({
    url: `${base}/package/${item.slug}`,
  }));
  return [...staticRoutes, ...packageRoutes];
}
