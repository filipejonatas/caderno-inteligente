/**
 * Key paths shared by the frontend fixtures and the real API (tests/test_frontend_contracts.py).
 * Children of dynamic maps (keyed by SKU, rule code, sheet…) are not traversed.
 */
import contract from './contract-keys.json';

export const DYNAMIC_KEYS = new Set<string>(contract.dynamic_keys);

export function keyPaths(value: unknown, prefix = '', paths = new Set<string>()): Set<string> {
  if (Array.isArray(value)) {
    for (const item of value) keyPaths(item, `${prefix}[]`, paths);
  } else if (value && typeof value === 'object') {
    for (const [key, child] of Object.entries(value)) {
      const path = prefix ? `${prefix}.${key}` : key;
      paths.add(path);
      if (!DYNAMIC_KEYS.has(key)) keyPaths(child, path, paths);
    }
  }
  return paths;
}

export const endpoints = contract.endpoints as Record<string, { path: string; keys: string[] }>;
