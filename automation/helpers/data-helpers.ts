/**
 * Data Helpers
 * ============
 * 
 * Utility functions for reading test data from JSON files,
 * environment variables, and other data sources.
 */

import * as fs from 'fs';
import * as path from 'path';

/**
 * Read JSON data from a file
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function readJsonData<T = any>(filePath: string): T {
  try {
    const fullPath = path.resolve(filePath);
    const fileContent = fs.readFileSync(fullPath, 'utf-8');
    return JSON.parse(fileContent) as T;
  } catch (error) {
    throw new Error('Failed to read JSON file at ' + filePath + ': ' + String(error));
  }
}

/**
 * Get environment variable with fallback
 */
export function getEnvVar(key: string, fallback?: string): string {
  const value = process.env[key];
  if (value === undefined && fallback === undefined) {
    throw new Error('Environment variable ' + key + ' is not set');
  }
  return value || fallback || '';
}

/**
 * Get test data from the data directory
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function getTestData<T = any>(fileName: string): T {
  const dataPath = path.join(__dirname, '..', 'data', fileName);
  return readJsonData<T>(dataPath);
}

/**
 * Parse string to JSON with error handling
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function parseJsonSafe(jsonString: string, fallback?: any): any {
  try {
    return JSON.parse(jsonString);
  } catch (error) {
    if (fallback !== undefined) {
      return fallback;
    }
    throw new Error('Failed to parse JSON: ' + String(error));
  }
}
