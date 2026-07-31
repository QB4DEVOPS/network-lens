import { useCallback, useEffect, useRef, useState } from "react";
import Editor, { OnMount } from "@monaco-editor/react";
import type { editor as MonacoEditor } from "monaco-editor";
import { validateBackend, validateSync, type BackendManifest } from "./apiContract";

const API_PORT = import.meta.env.VITE_API_PORT || "8000";

const DEFAULT_CLI = `hostn R1
int lo0
no sh
ip add 10.0.0.1 255.255.255.255
ipv6 enable
ipv6 address 2001:db8::1/64
ipv6 address 2001:db8:1::1/64`;

const INITIAL_NAC = `# Network Lens — Live NaC preview
# Schema: iosxe-devices-configuration-mvp
# Schema version: 3.0.0
# Canonical root: iosxe.devices[]
# Contract: lean iosxe.devices[].configuration.*
# Model docs: https://netascode.cisco.com/docs/data_models/iosxe/overview/
# Module: netascode/nac-iosxe/iosxe 0.1.0
# Generated · Not applied
# Apply-safe: only interfaces you typed in CLI — no placeholder resources

iosxe:
  devices:
  - name: iosv-01
    configuration:
      system:
        hostname: null  # ← type: hostn R1
      interfaces:
        # ← type: int lo0, int g0/0/0, int tun10, int vlan888
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

export default function App() {
  const [cliText, setCliText] = useState(DEFAULT_CLI);
  const [nacYaml, setNacYaml] = useState(INITIAL_NAC);
  const [warnings, setWarnings] = useState<ParseWarning[]>([]);
  const [, setMappings] = useState<LineMapping[]>([]);
  const [linkLabel, setLinkLabel] = useState<string | null>(null);
  const [cliContext, setCliContext] = useState<string | null>(null);
  const [backendInfo, setBackendInfo] = useState<BackendManifest | null>(null);
  const [backendIssue, setBackendIssue] = useState<string | null>(null);
  const [status, setStatus] = useState<"idle" | "syncing" | "error">("idle");

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const cliEditorRef = useRef<MonacoEditor.IStandaloneCodeEditor | null>(null);
  const yamlEditorRef = useRef<MonacoEditor.IStandaloneCodeEditor | null>(null);
  const cliDecoRef = useRef<string[]>([]);
  const yamlDecoRef = useRef<string[]>([]);
  const mappingsRef = useRef<LineMapping[]>([]);
  const contextByLineRef = useRef<Record<string, string | null>>({});

  const clearHighlights = useCallback(() => {
    if (cliEditorRef.current) {
      cliDecoRef.current = cliEditorRef.current.deltaDecorations(cliDecoRef.current, []);
    }
    if (yamlEditorRef.current) {
      yamlDecoRef.current = yamlEditorRef.current.deltaDecorations(yamlDecoRef.current, []);
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

    if (yamlEditorRef.current) {
      yamlDecoRef.current = yamlEditorRef.current.deltaDecorations(yamlDecoRef.current, [
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
      ]);
      yamlEditorRef.current.revealLineInCenterIfOutsideViewport(mapping.yaml_start_line);
    }
  }, []);

  const updateCliContext = useCallback((lineNumber: number) => {
    setCliContext(contextAtLine(contextByLineRef.current, lineNumber));
  }, []);

  const highlightFromCli = useCallback(
    (lineNumber: number) => {
      updateCliContext(lineNumber);
      const mapping = pickCliMapping(mappingsRef.current, lineNumber);
      if (!mapping) {
        clearHighlights();
        return;
      }
      applyMapping(mapping);
    },
    [applyMapping, clearHighlights, updateCliContext],
  );

  const highlightFromYaml = useCallback(
    (lineNumber: number) => {
      const mapping = pickYamlMapping(mappingsRef.current, lineNumber);
      if (!mapping) {
        clearHighlights();
        return;
      }
      applyMapping(mapping);
    },
    [applyMapping, clearHighlights],
  );

  const onCliMount: OnMount = (editor) => {
    cliEditorRef.current = editor;
    editor.onDidChangeCursorPosition((e) => highlightFromCli(e.position.lineNumber));
  };

  const onYamlMount: OnMount = (editor) => {
    yamlEditorRef.current = editor;
    editor.onDidChangeCursorPosition((e) => highlightFromYaml(e.position.lineNumber));
  };

  const sync = useCallback(
    async (text: string) => {
      setStatus("syncing");
      try {
        const res = await fetch("/sync", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ cli_text: text }),
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
        if (issue) {
          setStatus("error");
          return;
        }

        setNacYaml(data.nac_yaml);
        setWarnings(data.warnings ?? []);
        const nextMappings: LineMapping[] = data.mappings ?? [];
        setMappings(nextMappings);
        mappingsRef.current = nextMappings;
        contextByLineRef.current = data.context_by_line ?? {};

        const cliLine = cliEditorRef.current?.getPosition()?.lineNumber;
        if (cliLine) {
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
    [applyMapping, clearHighlights, updateCliContext],
  );

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
    debounceRef.current = setTimeout(() => sync(cliText), 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [cliText, sync]);

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
          {cliContext ? (
            <span className="badge muted">↳ {cliContext}</span>
          ) : (
            <span className="badge muted">Global config</span>
          )}
          {backendInfo?.build_id && !backendIssue && (
            <span className="badge muted">API {backendInfo.api_version} · {backendInfo.build_id}</span>
          )}
          {linkLabel && <span className="badge link">↔ {linkLabel}</span>}
          {status === "syncing" && <span className="badge muted">Syncing…</span>}
          {backendIssue && <span className="badge error">{backendIssue}</span>}
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
        <section className="pane">
          <div className="pane-header">
            <span className="pane-label">CLI input</span>
            <span className="pane-hint">Click a line ↔ highlights nac.yaml · lo 999, g 0/0, tun 10, vlan 888</span>
          </div>
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
        </section>

        <section className="pane">
          <div className="pane-header">
            <span className="pane-label">nac.yaml</span>
            <span className="pane-hint">Generated preview · read-only · iosxe.devices[]</span>
          </div>
          <Editor
            height="100%"
            language="yaml"
            theme="vs-dark"
            value={nacYaml}
            onMount={onYamlMount}
            options={{
              readOnly: true,
              minimap: { enabled: false },
              fontSize: 14,
              lineNumbers: "on",
              scrollBeyondLastLine: false,
              wordWrap: "on",
            }}
          />
        </section>
      </main>
    </div>
  );
}
