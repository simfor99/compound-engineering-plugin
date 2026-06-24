import { createHash } from "node:crypto"
import { promises as fs } from "node:fs"
import path from "node:path"

export type CeBundleManifestFile = {
  path: string
  sha256: string
}

export type CeBundleManifest = {
  schemaVersion: 1
  bundleVersion: string
  scope: string
  files: CeBundleManifestFile[]
}

const BUNDLE_MANIFEST_PATH = path.join("skills", "shared", "ce-bundle.json")
const REQUIRED_BUNDLE_SCOPE_PATHS = [
  "AGENTS.md",
  "package.json",
  "skills",
  "src/release",
  "scripts/release",
  ".opencode",
  ".pi",
  ".agents/plugins/marketplace.json",
  ".agy/plugin.json",
  ".claude-plugin/marketplace.json",
  ".claude-plugin/plugin.json",
  ".codex-plugin/plugin.json",
  ".cursor-plugin/marketplace.json",
  ".cursor-plugin/plugin.json",
]
const EXCLUDED_BUNDLE_PATHS = new Set([
  BUNDLE_MANIFEST_PATH,
])
const IGNORED_DIRS = new Set([
  ".git",
  ".pytest_cache",
  "__pycache__",
  "node_modules",
])
const IGNORED_FILES = new Set([
  ".DS_Store",
])

function isSafeRelativePath(relativePath: string): boolean {
  if (!relativePath || path.isAbsolute(relativePath)) return false
  const normalized = path.normalize(relativePath)
  return normalized === relativePath && !normalized.startsWith("..") && !normalized.includes(`${path.sep}..${path.sep}`)
}

async function sha256File(filePath: string): Promise<string> {
  const contents = await fs.readFile(filePath)
  return createHash("sha256").update(contents).digest("hex")
}

function toManifestPath(relativePath: string): string {
  return relativePath.split(path.sep).join("/")
}

async function exists(root: string, relativePath: string): Promise<boolean> {
  try {
    await fs.stat(path.join(root, relativePath))
    return true
  } catch (err: unknown) {
    if ((err as NodeJS.ErrnoException).code === "ENOENT") {
      return false
    }
    throw err
  }
}

function shouldIgnore(relativePath: string): boolean {
  const manifestPath = toManifestPath(relativePath)
  const parts = manifestPath.split("/")
  return (
    EXCLUDED_BUNDLE_PATHS.has(manifestPath) ||
    parts.some((part) => IGNORED_DIRS.has(part)) ||
    IGNORED_FILES.has(parts.at(-1) ?? "") ||
    manifestPath.endsWith(".pyc")
  )
}

async function listFiles(root: string, relativePath: string): Promise<string[]> {
  const absolutePath = path.join(root, relativePath)
  const stat = await fs.stat(absolutePath)

  if (stat.isFile()) {
    return shouldIgnore(relativePath) ? [] : [toManifestPath(relativePath)]
  }
  if (!stat.isDirectory()) {
    return []
  }

  const entries = await fs.readdir(absolutePath, { withFileTypes: true })
  const nested = await Promise.all(entries.map((entry) => (
    listFiles(root, path.join(relativePath, entry.name))
  )))
  return nested.flat().filter((entry) => !shouldIgnore(entry)).sort()
}

async function expectedBundleFiles(root: string, errors: string[]): Promise<Set<string>> {
  const existingScopePaths: string[] = []
  for (const entry of REQUIRED_BUNDLE_SCOPE_PATHS) {
    if (await exists(root, entry)) {
      existingScopePaths.push(entry)
    } else {
      errors.push(`${entry} required by ${BUNDLE_MANIFEST_PATH} scope is missing`)
    }
  }

  const files = await Promise.all(existingScopePaths.map((entry) => listFiles(root, entry)))
  return new Set(files.flat().sort())
}

export async function readCeBundleManifest(root = process.cwd()): Promise<CeBundleManifest> {
  const manifestPath = path.join(root, BUNDLE_MANIFEST_PATH)
  const raw = await fs.readFile(manifestPath, "utf8")
  return JSON.parse(raw) as CeBundleManifest
}

export async function validateCeBundleManifest(root = process.cwd()): Promise<string[]> {
  const errors: string[] = []
  let manifest: CeBundleManifest

  try {
    manifest = await readCeBundleManifest(root)
  } catch (err: unknown) {
    if ((err as NodeJS.ErrnoException).code === "ENOENT") {
      return [`${BUNDLE_MANIFEST_PATH} is missing`]
    }
    return [`${BUNDLE_MANIFEST_PATH} could not be read: ${(err as Error).message}`]
  }

  if (manifest.schemaVersion !== 1) {
    errors.push(`${BUNDLE_MANIFEST_PATH} schemaVersion must be 1`)
  }
  if (!manifest.bundleVersion) {
    errors.push(`${BUNDLE_MANIFEST_PATH} bundleVersion is required`)
  }
  if (!Array.isArray(manifest.files) || manifest.files.length === 0) {
    errors.push(`${BUNDLE_MANIFEST_PATH} must list at least one file`)
    return errors
  }

  const seen = new Set<string>()
  const expectedFiles = await expectedBundleFiles(root, errors)
  for (const entry of manifest.files) {
    if (!entry?.path || !entry?.sha256) {
      errors.push(`${BUNDLE_MANIFEST_PATH} contains an invalid file entry`)
      continue
    }
    if (!isSafeRelativePath(entry.path)) {
      errors.push(`${BUNDLE_MANIFEST_PATH} contains unsafe path: ${entry.path}`)
      continue
    }
    if (seen.has(entry.path)) {
      errors.push(`${BUNDLE_MANIFEST_PATH} contains duplicate path: ${entry.path}`)
      continue
    }
    seen.add(entry.path)
    if (!expectedFiles.has(entry.path)) {
      errors.push(`${entry.path} is outside the expected ${BUNDLE_MANIFEST_PATH} scope`)
      continue
    }

    const absolutePath = path.join(root, entry.path)
    let actual: string
    try {
      actual = await sha256File(absolutePath)
    } catch (err: unknown) {
      if ((err as NodeJS.ErrnoException).code === "ENOENT") {
        errors.push(`${entry.path} listed in ${BUNDLE_MANIFEST_PATH} is missing`)
        continue
      }
      throw err
    }

    if (actual !== entry.sha256) {
      errors.push(`${entry.path} checksum mismatch in ${BUNDLE_MANIFEST_PATH}`)
    }
  }

  for (const expectedPath of expectedFiles) {
    if (!seen.has(expectedPath)) {
      errors.push(`${expectedPath} is missing from ${BUNDLE_MANIFEST_PATH}`)
    }
  }

  return errors
}
