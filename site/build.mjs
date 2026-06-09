import { mkdir, readdir, readFile, writeFile } from "node:fs/promises";
import { extname, join } from "node:path";

const rootDir = new URL(".", import.meta.url).pathname;
const publicDir = join(rootDir, "public");
const distDir = join(rootDir, "dist");

const contentTypes = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".svg": "image/svg+xml; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".txt": "text/plain; charset=utf-8"
};

const assets = {};

async function walk(directory, prefix = "") {
  const entries = await readdir(directory, { withFileTypes: true });
  for (const entry of entries) {
    const absolutePath = join(directory, entry.name);
    const relativePath = `${prefix}/${entry.name}`;
    if (entry.isDirectory()) {
      await walk(absolutePath, relativePath);
      continue;
    }
    const body = await readFile(absolutePath, "utf8");
    const normalizedPath = relativePath === "/index.html" ? "/" : relativePath;
    assets[normalizedPath] = {
      body,
      contentType: contentTypes[extname(entry.name)] || "application/octet-stream"
    };
  }
}

await walk(publicDir);
await mkdir(distDir, { recursive: true });

const workerSource = `const assets = ${JSON.stringify(assets, null, 2)};

export default {
  async fetch(request) {
    const url = new URL(request.url);
    const path = url.pathname === "/" ? "/" : url.pathname.replace(/\\/$/, "");
    const asset = assets[path] || assets[\`\${path}.html\`] || assets["/404.html"];
    const status = asset === assets["/404.html"] && path !== "/404.html" ? 404 : 200;
    return new Response(asset.body, {
      status,
      headers: {
        "content-type": asset.contentType,
        "cache-control": "public, max-age=300",
        "x-content-type-options": "nosniff"
      }
    });
  }
};
`;

await writeFile(join(distDir, "worker.mjs"), workerSource, "utf8");
console.log(`Built ${Object.keys(assets).length} assets into site/dist/worker.mjs`);

