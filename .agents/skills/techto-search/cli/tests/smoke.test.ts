import { test, expect } from "bun:test";
import { $ } from "bun";

test("techto-search CLI returns results for valid query", async () => {
  const res = await $`bun run src/cli.ts search -q "systems" --limit 5 --format json`.nothrow();
  expect(res.exitCode).toBe(0);
  const data = JSON.parse(res.stdout.toString());
  expect(data.meta).toBeDefined();
  expect(Array.isArray(data.results)).toBe(true);
});

test("techto-search CLI fails when query is missing", async () => {
  const res = await $`bun run src/cli.ts search`.nothrow();
  expect(res.exitCode).toBe(1);
});
