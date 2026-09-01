const cache = new Map();

export function cacheKey(name, parts = []) {
  return [name, ...parts.map((part) => String(part ?? ""))].join(":");
}

export async function cached(key, ttlMs, loader) {
  const hit = cache.get(key);
  if (hit && hit.expires > Date.now()) return hit.value;
  const value = await loader();
  cache.set(key, { value, expires: Date.now() + ttlMs });
  return value;
}

export function clearDataCaches() {
  cache.clear();
}
