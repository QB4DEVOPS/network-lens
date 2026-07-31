/** Keep in sync with backend/app/version.py FEATURES */
export const REQUIRED_FEATURES = [
  "ipv6_unicast_routing",
  "cli_context_by_line",
] as const;

export interface BackendManifest {
  api_version?: string;
  build_id?: string;
  features?: string[];
  pid?: number;
}

export interface SyncPayload extends BackendManifest {
  nac_yaml: string;
  warnings?: unknown[];
  mappings?: unknown[];
  context_by_line?: Record<string, string | null>;
  canonical?: {
    system?: {
      hostname?: string | null;
      ipv6_unicast_routing?: boolean;
    };
  };
}

export function validateBackend(manifest: BackendManifest | null | undefined): string | null {
  if (!manifest?.features?.length) {
    return "Backend missing features manifest — restart with backend\\run.bat";
  }
  for (const feature of REQUIRED_FEATURES) {
    if (!manifest.features.includes(feature)) {
      return `Backend too old (missing ${feature}) — restart with backend\\run.bat`;
    }
  }
  return null;
}

export function validateSync(cliText: string, data: SyncPayload): string | null {
  const manifestError = validateBackend(data);
  if (manifestError) {
    return manifestError;
  }

  if (cliText.trim() && data.context_by_line === undefined) {
    return "Backend missing context_by_line — restart with backend\\run.bat";
  }

  if (/ipv6 unicast-routing/i.test(cliText) && !data.canonical?.system?.ipv6_unicast_routing) {
    return 'CLI has "ipv6 unicast-routing" but API ignored it — stale backend? Run validate.bat';
  }

  if (/ipv6 unicast-routing/i.test(cliText) && !data.nac_yaml.includes("ipv6_unicast_routing:")) {
    return "ipv6 unicast-routing missing from generated YAML — stale backend? Run validate.bat";
  }

  return null;
}
