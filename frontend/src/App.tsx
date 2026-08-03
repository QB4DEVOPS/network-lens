import { useCallback, useEffect, useRef, useState } from "react";
import Editor, { OnMount } from "@monaco-editor/react";
import type { editor as MonacoEditor } from "monaco-editor";
import { validateBackend, validateSync, mappingFeatureWarning, type BackendManifest } from "./apiContract";
import { SplitPane } from "./SplitPane";

const API_PORT = import.meta.env.VITE_API_PORT || "8000";
const SHOW_HINTS_KEY = "network-lens-show-hints";

const DEFAULT_CLI = `hostn R1
int lo0
no sh
ip add 10.0.0.1 255.255.255.255
ipv6 enable
ipv6 address 2001:db8::1/64
ipv6 address 2001:db8:1::1/64`;

const INITIAL_NAC = `# Network Lens — Live NaC preview
# Schema: iosxe-devices-configuration-full
# Schema version: 4.0.0
# Scaffold hints: off — only typed CLI appears in YAML

iosxe:
  devices:
  - name: iosv-01
    configuration:
      interfaces:
`;

const INITIAL_HCL = `# Network Lens — Terraform preview
# Generated · Not applied
# Provider: CiscoDevNet/iosxe (scaffold only)
# NaC path → TF resource:
#   iosxe.devices[].configuration.system.*     → iosxe_system
#   iosxe.devices[].configuration.interfaces.loopbacks[] → iosxe_interface_loopback

resource "iosxe_system" "r1" {
  hostname = null # ← type: hostn R1
}

resource "iosxe_interface_loopback" "lo0" {
  name              = 0
  shutdown          = true
  ipv4_address      = null # ← type: interface lo0, no shutdown, ip address ...
  ipv4_address_mask = null
}
`;

const INITIAL_JSON = `{
  "_network_lens_preview": {
    "generated": "Not applied",
    "dialect": "RESTCONF JSON (OpenConfig interfaces + IOS-XE native subset)",
    "nac_path": "iosxe.devices[].configuration → ietf-interfaces + Cisco-IOS-XE-native"
  },
  "ietf-interfaces:interfaces": {
    "interface": []
  },
  "Cisco-IOS-XE-native:native": {
    "hostname": null
  }
}
`;

interface ParseWarning {
  line: number;
  message: string;
  cli_line: string;
}

interface LineMapping {
  cli_line: number;
  yaml_start_line: number;
  yaml_end_line: number;
  label: string;
  field_key: string;
}

function mappingSpecificity(fieldKey: string): number {
  if (
    fieldKey.endsWith(":ipv4") ||
    fieldKey.endsWith(":ipv6") ||
    fieldKey.endsWith(":shutdown") ||
    fieldKey.endsWith(":description")
  ) {
    return 3;
  }
  if (fieldKey.startsWith("interface:")) {
    return 2;
  }
  if ((fieldKey.startsWith("crypto.") || fieldKey.startsWith("aaa.")) && fieldKey.includes(":")) {
    return 2 + (fieldKey.match(/:/g)?.length ?? 0);
  }
  if (fieldKey.startsWith("ntp.") && fieldKey.includes(":")) {
    return 2;
  }
  return 1;
}

function pickCliMapping(mappings: LineMapping[], cliLine: number): LineMapping | undefined {
  const matches = mappings.filter((m) => m.cli_line === cliLine);
  if (!matches.length) return undefined;
  return matches.sort((a, b) => mappingSpecificity(b.field_key) - mappingSpecificity(a.field_key))[0];
}

function pickYamlMapping(mappings: LineMapping[], yamlLine: number): LineMapping | undefined {
  const matches = mappings.filter(
    (m) => m.yaml_start_line <= yamlLine && yamlLine <= m.yaml_end_line,
  );
  if (!matches.length) return undefined;
  return matches.sort(
    (a, b) =>
      a.yaml_end_line - a.yaml_start_line - (b.yaml_end_line - b.yaml_start_line),
  )[0];
}

function contextAtLine(
  contextByLine: Record<string, string | null>,
  lineNumber: number,
): string | null {
  for (let line = lineNumber; line >= 1; line -= 1) {
    const key = String(line);
    if (key in contextByLine) {
      return contextByLine[key];
    }
  }
  return null;
}

type OutputFormat = "nac" | "json" | "hcl";

function programmaticLanguage(format: OutputFormat): string {
  if (format === "nac") return "yaml";
  if (format === "hcl") return "hcl";
  return "json";
}

function programmaticHint(format: OutputFormat): string {
  if (format === "nac") return "Generated preview · iosxe.devices[]";
  if (format === "hcl") return "NaC → iosxe_system + iosxe_interface_loopback";
  return "NaC → ietf-interfaces + Cisco-IOS-XE-native JSON";
}

export default function App() {
  const [cliText, setCliText] = useState(DEFAULT_CLI);
  const [nacYaml, setNacYaml] = useState(INITIAL_NAC);
  const [terraformHcl, setTerraformHcl] = useState(INITIAL_HCL);
  const [restconfJson, setRestconfJson] = useState(INITIAL_JSON);
  const [outputFormat, setOutputFormat] = useState<OutputFormat>("nac");
  const [warnings, setWarnings] = useState<ParseWarning[]>([]);
  const [, setMappings] = useState<LineMapping[]>([]);
  const [linkLabel, setLinkLabel] = useState<string | null>(null);
  const [cliContext, setCliContext] = useState<string | null>(null);
  const [backendInfo, setBackendInfo] = useState<BackendManifest | null>(null);
  const [backendIssue, setBackendIssue] = useState<string | null>(null);
  const [mappingIssue, setMappingIssue] = useState<string | null>(null);
  const [status, setStatus] = useState<"idle" | "syncing" | "error">("idle");
  const [showHints, setShowHints] = useState(() => localStorage.getItem(SHOW_HINTS_KEY) === "true");

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const cliEditorRef = useRef<MonacoEditor.IStandaloneCodeEditor | null>(null);
  const programmaticEditorRef = useRef<MonacoEditor.IStandaloneCodeEditor | null>(null);
  const cliDecoRef = useRef<string[]>([]);
  const programmaticDecoRef = useRef<string[]>([]);
  const mappingsRef = useRef<LineMapping[]>([]);
  const contextByLineRef = useRef<Record<string, string | null>>({});

  const clearHighlights = useCallback(() => {
    if (cliEditorRef.current) {
      cliDecoRef.current = cliEditorRef.current.deltaDecorations(cliDecoRef.current, []);
    }
    if (programmaticEditorRef.current) {
      programmaticDecoRef.current = programmaticEditorRef.current.deltaDecorations(
        programmaticDecoRef.current,
        [],
      );
    }
    setLinkLabel(null);
  }, []);

  const applyMapping = useCallback((mapping: LineMapping) => {
    setLinkLabel(mapping.label);

    if (cliEditorRef.current) {
      cliDecoRef.current = cliEditorRef.current.deltaDecorations(cliDecoRef.current, [
        {
          range: {
            startLineNumber: mapping.cli_line,
            startColumn: 1,
            endLineNumber: mapping.cli_line,
            endColumn: 1,
          },
          options: {
            isWholeLine: true,
            className: "line-highlight-linked",
            marginClassName: "line-highlight-margin",
          },
        },
      ]);
      cliEditorRef.current.revealLineInCenterIfOutsideViewport(mapping.cli_line);
    }

    if (outputFormat === "nac" && programmaticEditorRef.current) {
      programmaticDecoRef.current = programmaticEditorRef.current.deltaDecorations(
        programmaticDecoRef.current,
        [
          {
            range: {
              startLineNumber: mapping.yaml_start_line,
              startColumn: 1,
              endLineNumber: mapping.yaml_end_line,
              endColumn: 1,
            },
            options: {
              isWholeLine: true,
              className: "line-highlight-linked",
              marginClassName: "line-highlight-margin",
            },
          },
        ],
      );
      programmaticEditorRef.current.revealLineInCenterIfOutsideViewport(mapping.yaml_start_line);
    }
  }, [outputFormat]);

  const updateCliContext = useCallback((lineNumber: number) => {
    setCliContext(contextAtLine(contextByLineRef.current, lineNumber));
  }, []);

  const highlightFromCli = useCallback(
    (lineNumber: number) => {
      updateCliContext(lineNumber);
      if (outputFormat !== "nac") {
        clearHighlights();
        return;
      }
      const mapping = pickCliMapping(mappingsRef.current, lineNumber);
      if (!mapping) {
        clearHighlights();
        return;
      }
      applyMapping(mapping);
    },
    [applyMapping, clearHighlights, outputFormat, updateCliContext],
  );

  const highlightFromProgrammatic = useCallback(
    (lineNumber: number) => {
      if (outputFormat !== "nac") {
        clearHighlights();
        return;
      }
      const mapping = pickYamlMapping(mappingsRef.current, lineNumber);
      if (!mapping) {
        clearHighlights();
        return;
      }
      applyMapping(mapping);
    },
    [applyMapping, clearHighlights, outputFormat],
  );

  const onCliMount: OnMount = (editor) => {
    cliEditorRef.current = editor;
    editor.onDidChangeCursorPosition((e) => highlightFromCli(e.position.lineNumber));
  };

  const onProgrammaticMount: OnMount = (editor) => {
    programmaticEditorRef.current = editor;
    editor.onDidChangeCursorPosition((e) => highlightFromProgrammatic(e.position.lineNumber));
  };

  const switchOutputFormat = useCallback(
    (format: OutputFormat) => {
      setOutputFormat(format);
      if (format !== "nac") {
        clearHighlights();
      }
    },
    [clearHighlights],
  );

  const programmaticValue =
    outputFormat === "nac" ? nacYaml : outputFormat === "hcl" ? terraformHcl : restconfJson;

  const sync = useCallback(
    async (text: string, hints: boolean) => {
      setStatus("syncing");
      try {
        const res = await fetch("/sync", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ cli_text: text, show_hints: hints }),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        setBackendInfo({
          api_version: data.api_version,
          build_id: data.build_id,
          features: data.features,
          pid: data.pid,
        });

        const issue = validateSync(text, data);
        setBackendIssue(issue);
        setMappingIssue(issue ? null : mappingFeatureWarning(text, data));
        if (issue) {
          setStatus("error");
          return;
        }

        setNacYaml(data.nac_yaml);
        setTerraformHcl(data.terraform_hcl ?? INITIAL_HCL);
        setRestconfJson(data.restconf_json ?? INITIAL_JSON);
        setWarnings(data.warnings ?? []);
        const nextMappings: LineMapping[] = data.mappings ?? [];
        setMappings(nextMappings);
        mappingsRef.current = nextMappings;
        contextByLineRef.current = data.context_by_line ?? {};

        const cliLine = cliEditorRef.current?.getPosition()?.lineNumber;
        if (cliLine && outputFormat === "nac") {
          updateCliContext(cliLine);
          const mapping = pickCliMapping(nextMappings, cliLine);
          if (mapping) applyMapping(mapping);
          else clearHighlights();
        } else {
          clearHighlights();
        }
        setStatus("idle");
      } catch {
        setBackendIssue(`Cannot reach API on port ${API_PORT} — run backend\\run.bat`);
        setStatus("error");
      }
    },
    [applyMapping, clearHighlights, outputFormat, updateCliContext],
  );

  const toggleShowHints = useCallback(() => {
    setShowHints((prev) => {
      const next = !prev;
      localStorage.setItem(SHOW_HINTS_KEY, String(next));
      return next;
    });
  }, []);

  useEffect(() => {
    void (async () => {
      try {
        const res = await fetch("/health");
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const health = (await res.json()) as BackendManifest;
        setBackendInfo(health);
        setBackendIssue(validateBackend(health));
      } catch {
        setBackendIssue(`Cannot reach API on port ${API_PORT} — run backend\\run.bat`);
        setStatus("error");
      }
    })();
  }, []);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => sync(cliText, showHints), 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [cliText, showHints, sync]);

  return (
    <div className="app">
      <header className="header">
        <div className="brand">
          <span className="logo">◉</span>
          <h1>Network Lens</h1>
          <span className="tagline">Live NaC first · Programmatically first</span>
        </div>
        <div className="status-bar">
          <span className="badge">Branch Lab</span>
          <span className="badge">Live NaC</span>
          <span className="badge accent">Generated · Not applied</span>
          <button
            type="button"
            className={`hints-toggle${showHints ? " active" : ""}`}
            onClick={toggleShowHints}
            title="Show scaffold hints (# ← type: ...) for empty NaC sections"
            aria-pressed={showHints}
          >
            Hints {showHints ? "on" : "off"}
          </button>
          {cliContext ? (
            <span className="badge muted">↳ {cliContext}</span>
          ) : (
            <span className="badge muted">Global config</span>
          )}
          {backendInfo?.build_id && !backendIssue && (
            <span className="badge muted">API {backendInfo.api_version} · {backendInfo.build_id}</span>
          )}
          {linkLabel && outputFormat === "nac" && (
            <span className="badge link">↔ {linkLabel}</span>
          )}
          {status === "syncing" && <span className="badge muted">Syncing…</span>}
          {backendIssue && <span className="badge error">{backendIssue}</span>}
          {mappingIssue && <span className="badge error">{mappingIssue}</span>}
          {!backendIssue && status === "error" && (
            <span className="badge error">Backend offline — run backend\run.bat (port {API_PORT})</span>
          )}
        </div>
      </header>

      {warnings.length > 0 && (
        <div className="warnings-bar">
          {warnings.map((w) => (
            <div key={`${w.line}-${w.cli_line}`} className="warning-item">
              <span className="warning-line">Line {w.line}</span>
              <span className="warning-msg">{w.message}</span>
              <code className="warning-cli">{w.cli_line}</code>
            </div>
          ))}
        </div>
      )}

      <main className="panes">
        <SplitPane
          left={
            <section className="pane">
              <div className="pane-header">
                <span className="pane-label">CLI input</span>
                <span className="pane-hint">
                  {outputFormat === "nac"
                    ? "Click a line ↔ highlights nac.yaml"
                    : "Same canonical model · switch tabs to compare dialects"}
                </span>
              </div>
              <div className="pane-editor">
                <Editor
                  height="100%"
                  language="plaintext"
                  theme="vs-dark"
                  value={cliText}
                  onMount={onCliMount}
                  onChange={(v) => setCliText(v ?? "")}
                  options={{
                    minimap: { enabled: false },
                    fontSize: 14,
                    lineNumbers: "on",
                    scrollBeyondLastLine: false,
                    wordWrap: "on",
                  }}
                />
              </div>
            </section>
          }
          right={
            <section className="pane">
              <div className="pane-header">
                <div className="pane-header-left">
                  <div className="format-toggle" role="tablist" aria-label="Programmatic output format">
                    <button
                      type="button"
                      role="tab"
                      aria-selected={outputFormat === "nac"}
                      className={`format-toggle-btn${outputFormat === "nac" ? " active" : ""}`}
                      onClick={() => switchOutputFormat("nac")}
                    >
                      nac.yaml
                    </button>
                    <button
                      type="button"
                      role="tab"
                      aria-selected={outputFormat === "json"}
                      className={`format-toggle-btn${outputFormat === "json" ? " active" : ""}`}
                      onClick={() => switchOutputFormat("json")}
                    >
                      JSON
                    </button>
                    <button
                      type="button"
                      role="tab"
                      aria-selected={outputFormat === "hcl"}
                      className={`format-toggle-btn${outputFormat === "hcl" ? " active" : ""}`}
                      onClick={() => switchOutputFormat("hcl")}
                    >
                      HCL
                    </button>
                  </div>
                </div>
                <span className="pane-hint">{programmaticHint(outputFormat)}</span>
              </div>
              <div className="pane-editor">
                <Editor
                  height="100%"
                  language={programmaticLanguage(outputFormat)}
                  theme="vs-dark"
                  value={programmaticValue}
                  onMount={onProgrammaticMount}
                  options={{
                    readOnly: true,
                    minimap: { enabled: false },
                    fontSize: 14,
                    lineNumbers: "on",
                    scrollBeyondLastLine: false,
                    wordWrap: "on",
                  }}
                />
              </div>
            </section>
          }
        />
      </main>
    </div>
  );
}
