import { MagicCard } from "@/components/ui/magic-card";
import { ShimmerButton } from "@/components/ui/shimmer-button";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { motion } from "framer-motion";
import CodeMirror from "@uiw/react-codemirror";
import { useEffect, useState } from "react";

const FONT_GLYPH =
  "The quick brown fox jumps over the lazy dog 0123456789 !@#$%^&*()_+-=[]{};:<>,.?/~";

const LANGUAGES = [
  { value: "en", label: "English" },
  { value: "hi", label: "हिन्दी" },
  { value: "fr", label: "Français" },
  { value: "es", label: "Español" },
  { value: "pt", label: "Português" },
  { value: "ru", label: "Русский" },
  { value: "ko", label: "한국어" },
  { value: "ja", label: "日本語" },
  { value: "zh", label: "中文" },
  { value: "el", label: "Ελληνικά" },
  { value: "ar", label: "العربية" },
  { value: "hj", label: "حجازي" },
  { value: "uk", label: "Українська" },
];

const RUN_KEYS = ["Ctrl+Enter", "Shift+Enter", "Ctrl+Shift+Enter", "Ctrl+Alt+Enter"];
const STOP_KEYS = ["Escape Escape", "Shift+Escape", "Ctrl+Alt+Escape"];

type ThemeMap = Record<string, { name: string } & Record<string, string>>;
type FontMap = Record<string, { name: string; family: string }>;
type Config = Record<string, any>;

export default function App() {
  const [screen, setScreen] = useState<"setup" | "app" | "editor" | "credits">("setup");
  const [setupStep, setSetupStep] = useState(1);
  const [setupLocale, setSetupLocale] = useState("en");
  const [setupFont, setSetupFont] = useState("OpenDyslexic");
  const [setupTheme, setSetupTheme] = useState("light");

  const [theme, setTheme] = useState("light");
  const [font, setFont] = useState("OpenDyslexic");
  const [sound, setSound] = useState(true);
  const [speak, setSpeak] = useState(false);
  const [code, setCode] = useState("# Your code starts here\n");
  const [credits, setCredits] = useState<string[]>([]);
  const [glossary, setGlossary] = useState<any[]>([]);
  const [trace, setTrace] = useState<any>(null);
  const [showGlossary, setShowGlossary] = useState(false);
  const [showTrace, setShowTrace] = useState(false);
  const [shellSession, setShellSession] = useState<string | null>(null);
  const [shellOpen, setShellOpen] = useState(false);
  const [shellOutput, setShellOutput] = useState("");
  const [shellInput, setShellInput] = useState("");
  const [fontUploadStatus, setFontUploadStatus] = useState("");
  const [version, setVersion] = useState("2.0.0-beta");
  const [config, setConfig] = useState<Config | null>(null);
  const [themes, setThemes] = useState<ThemeMap>({});
  const [fonts, setFonts] = useState<FontMap>({});
  const [loaded, setLoaded] = useState(false);

  const [runResult, setRunResult] = useState<{
    output: string;
    error: string;
    awaiting_answer: boolean;
    stopped: boolean;
    trace?: any;
  } | null>(null);
  const [runAnswers, setRunAnswers] = useState<string[]>([]);
  const [answerInput, setAnswerInput] = useState("");
  const [customSaved, setCustomSaved] = useState(false);
  const [runKey, setRunKey] = useState("Ctrl+Enter");
  const [stopKey, setStopKey] = useState("Escape Escape");
  const [recording, setRecording] = useState<"run" | "stop" | null>(null);
  const [recordingStatus, setRecordingStatus] = useState("");
  const [autoUpdate, setAutoUpdate] = useState(true);
  const [updateChannel, setUpdateChannel] = useState("beta");
  const [updateStatus, setUpdateStatus] = useState("");
  const [updateAvailable, setUpdateAvailable] = useState(false);
  const [updateInstalled, setUpdateInstalled] = useState(false);

  useEffect(() => {
    let active = true;
    Promise.all([
      fetch("/api/config").then((r) => r.json()),
      fetch("/api/themes").then((r) => r.json()),
      fetch("/api/fonts").then((r) => r.json()),
      fetch("/api/credits").then((r) => r.json()),
      fetch("/api/glossary").then((r) => r.json()).catch(() => []),
      fetch("/api/version").then((r) => r.json()).catch(() => ({ version: "2.0.0-beta" })),
    ])
      .then(([cfg, themeMap, fontMap, creditList, glossaryList, versionInfo]) => {
        if (!active) return;
        setConfig(cfg);
        setThemes(themeMap);
        setFonts(fontMap);
        setCredits(Array.isArray(creditList) ? creditList : []);
        setGlossary(Array.isArray(glossaryList) ? glossaryList : []);
        setVersion(versionInfo?.version || "2.0.0-beta");
        setTheme(cfg.theme || "light");
        setFont(cfg.font || "OpenDyslexic");
        setSound(!!cfg.sound_enabled);
        setSpeak(!!cfg.tts_enabled);
        setRunKey(cfg.run_key || "Ctrl+Enter");
        setStopKey(cfg.stop_key || "Escape Escape");
        setAutoUpdate(!!cfg.auto_update);
        setUpdateChannel(cfg.update_channel || "beta");
        setSetupLocale(cfg.locale || "en");
        setSetupFont(cfg.font || "OpenDyslexic");
        setSetupTheme(cfg.theme || "light");
        setLoaded(true);
      })
      .catch(() => setLoaded(true));
    return () => {
      active = false;
    };
  }, []);

  const selectedFont = fonts[setupFont] || fonts[font] || Object.values(fonts)[0];
  const selectedFontFamily = selectedFont?.family || "sans-serif";
  const selectedFontLabel = selectedFont?.name || setupFont;
  const readingFont = fonts[font] || Object.values(fonts)[0];
  const readingFontFamily = readingFont?.family || "sans-serif";

  useEffect(() => {
    if (!loaded) return;
    document.body.setAttribute("data-theme", theme);
    document.documentElement.classList.toggle("dark", theme !== "light" && theme !== "pastel" && theme !== "white");
    const family = fonts[font]?.family;
    if (family) {
      document.body.style.setProperty("--font-ui", family);
      document.body.style.fontFamily = family;
    }
    if (config) {
      document.body.style.setProperty("--font-size", `${config.font_size}px`);
      document.body.style.setProperty("--font-weight", String(config.font_weight || 400));
      document.body.style.setProperty("--line-height", String(config.line_height || 1.5));
      document.body.style.setProperty("--letter-spacing", `${config.letter_spacing || 0.5}px`);
      document.body.style.setProperty("--word-spacing", `${config.word_spacing ?? 0.5}px`);
    }
  }, [loaded, theme, font, fonts, config]);

  useEffect(() => {
    if (!recording) return;
    const handler = (e: KeyboardEvent) => {
      const mods: string[] = [];
      if (e.ctrlKey || e.metaKey) mods.push("Ctrl");
      if (e.altKey) mods.push("Alt");
      if (e.shiftKey) mods.push("Shift");
      if (e.key === "Control" || e.key === "Alt" || e.key === "Shift" || e.key === "Meta") {
        e.preventDefault();
        return;
      }
      if (e.key === "Escape" && mods.length === 0) {
        setRecording(null);
        setRecordingStatus("");
        e.preventDefault();
        return;
      }
      if (!/^[A-Za-z0-9_]+$/.test(e.key)) return;
      if (mods.length === 0) return;
      const combo = [...mods, e.key].join("+");
      const base = combo.split("+").pop() || "";
      if (base === "Ctrl" || base === "Alt" || base === "Shift") return;
      if (recording === "run") {
        setRunKey(combo);
        saveConfig({ run_key: combo });
      } else {
        setStopKey(combo);
        saveConfig({ stop_key: combo });
      }
      setRecording(null);
      setRecordingStatus("Saved.");
      e.preventDefault();
      e.stopPropagation();
    };
    document.addEventListener("keydown", handler, true);
    return () => document.removeEventListener("keydown", handler, true);
  }, [recording]);

  const checkUpdate = async () => {
    try {
      const res = await fetch("/api/update/check", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ force: true }),
      });
      const data = await res.json();
      setUpdateAvailable(!!data.update_available);
      setUpdateStatus(data.update_available ? `Update ${data.latest} available.` : "No update available.");
    } catch {
      setUpdateStatus("Update check failed.");
    }
  };

  const installUpdate = async () => {
    try {
      const res = await fetch("/api/update/install", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      const data = await res.json();
      if (data?.success) {
        setUpdateInstalled(true);
        setUpdateStatus(`Downloaded ${data.version}.`);
      } else {
        setUpdateStatus(data?.error_text || data?.error || "Install failed.");
      }
    } catch {
      setUpdateStatus("Install failed.");
    }
  };

  const applyUpdate = async () => {
    try {
      await fetch("/api/update/apply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      setUpdateInstalled(false);
      setUpdateStatus("Restarting to apply update.");
    } catch {
      setUpdateStatus("Apply failed.");
    }
  };

  const saveConfig = async (patch: Record<string, any>) => {
    const next = { ...(config || {}), ...patch };
    setConfig(next);
    if (patch.theme !== undefined) setTheme(patch.theme);
    if (patch.font !== undefined) setFont(patch.font);
    if (patch.sound_enabled !== undefined) setSound(!!patch.sound_enabled);
    if (patch.tts_enabled !== undefined) setSpeak(!!patch.tts_enabled);
    try {
      const res = await fetch("/api/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(patch),
      });
      const data = await res.json();
      if (data?.config) setConfig(data.config);
    } catch {
      // Keep the optimistic update; the next load will reconcile.
    }
  };

  const deleteFont = async (key: string) => {
    try {
      const res = await fetch("/api/fonts/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key }),
      });
      const data = await res.json();
      if (data?.success) {
        const fresh = await fetch("/api/fonts").then((r) => r.json());
        setFonts(fresh);
        if (data.config) setConfig(data.config);
        setFontUploadStatus(`Removed ${key}.`);
      } else {
        setFontUploadStatus(data?.error || "Remove failed.");
      }
    } catch {
      setFontUploadStatus("Remove failed.");
    }
  };

  const uploadFont = async (file: File) => {
    const form = new FormData();
    form.append("font", file);
    try {
      const res = await fetch("/api/fonts/upload", { method: "POST", body: form });
      const data = await res.json();
      if (data?.success && data.font) {
        const fresh = await fetch("/api/fonts").then((r) => r.json());
        setFonts(fresh);
        await saveConfig({ font: data.key });
        setFontUploadStatus(`Added ${data.key}.`);
      } else {
        setFontUploadStatus(data?.error || "Upload failed.");
      }
    } catch {
      setFontUploadStatus("Upload failed.");
    }
  };

  const startShell = async () => {
    try {
      const res = await fetch("/api/shell/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      const data = await res.json();
      if (data?.success) {
        setShellSession(data.session);
        setShellOpen(true);
      }
    } catch {
      setShellOutput((prev) => `${prev}\nShell failed to start.`);
    }
  };

  const runShell = async () => {
    if (!shellSession) await startShell();
    const session = shellSession;
    if (!session) return;
    try {
      const res = await fetch("/api/shell/exec", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session, code: shellInput }),
      });
      const data = await res.json();
      const output = [data?.output || "", data?.error || ""].filter(Boolean).join("\\n");
      setShellOutput((prev) => `${prev}\\n>>> ${shellInput}\\n${output}`.trim());
      setShellInput("");
    } catch {
      setShellOutput((prev) => `${prev}\\nShell request failed.`);
    }
  };

  const resetShell = async () => {
    if (!shellSession) return;
    await fetch("/api/shell/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session: shellSession }),
    });
    setShellOutput("");
  };

  const stopShell = async () => {
    if (!shellSession) return;
    await fetch("/api/shell/stop", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session: shellSession }),
    });
    setShellSession(null);
    setShellOpen(false);
    setShellOutput((prev) => `${prev}\\nShell stopped.`);
  };

  const submitAnswer = async () => {
    const nextAnswers = [...runAnswers, answerInput];
    setRunAnswers(nextAnswers);
    setAnswerInput("");
    try {
      const res = await fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code, answers: nextAnswers }),
      });
      const data = await res.json();
      setRunResult({
        output: data.output ?? "",
        error: data.error ?? "",
        awaiting_answer: !!data.awaiting_answer,
        stopped: !!data.stopped,
        trace: data.trace || null,
      });
      setTrace(data.trace || null);
    } catch {
      setRunResult({ output: "", error: "Run failed.", awaiting_answer: false, stopped: false });
    }
  };

  const clearOutput = () => {
    setRunResult(null);
    setRunAnswers([]);
    setAnswerInput("");
    setTrace(null);
  };

  const resetConfig = async () => {
    await fetch("/api/config/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    const cfg = await fetch("/api/config").then((r) => r.json());
    setConfig(cfg);
    setTheme(cfg.theme || "light");
    setFont(cfg.font || "OpenDyslexic");
    setSound(!!cfg.sound_enabled);
    setSpeak(!!cfg.tts_enabled);
    setSetupLocale(cfg.locale || "en");
    setSetupFont(cfg.font || "OpenDyslexic");
    setSetupTheme(cfg.theme || "light");
  };

  if (screen === "setup") {
    return (
      <main className="min-h-svh bg-background text-foreground">
        <div className="mx-auto flex max-w-2xl flex-col gap-6 p-8">
          <MagicCard className="p-8">
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35, ease: "easeOut" }}
            >
              <Badge variant="secondary">Setup</Badge>
              <h1 className="mt-2 text-3xl font-semibold tracking-tight">
                Step {setupStep} of 3
              </h1>
              <p className="text-muted-foreground">
                {setupStep === 1 && "Choose your language."}
                {setupStep === 2 && "Choose your reading font."}
                {setupStep === 3 && "Choose your theme."}
              </p>
            </motion.div>
          </MagicCard>

          <Card>
            <CardHeader>
              <CardTitle>Setup panel</CardTitle>
              <CardDescription>The next choice is one tap away.</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-6">
              {setupStep === 1 ? (
                <div className="flex items-center justify-between">
                  <Label htmlFor="setup-locale">Language</Label>
                  <Select
                    value={setupLocale}
                    onValueChange={(v) => {
                      if (!v) return;
                      setSetupLocale(v);
                      saveConfig({ locale: v });
                    }}
                  >
                    <SelectTrigger id="setup-locale" className="w-48">
                      <SelectValue placeholder="Language" />
                    </SelectTrigger>
                    <SelectContent>
                      {LANGUAGES.map((l) => (
                        <SelectItem key={l.value} value={l.value}>
                          {l.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              ) : null}

              {setupStep === 2 ? (
                <div className="flex flex-col gap-4">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="setup-font">Reading font</Label>
                    <Select
                      value={setupFont}
                      onValueChange={(v) => {
                        if (!v) return;
                        setSetupFont(v);
                        saveConfig({ font: v });
                      }}
                    >
                      <SelectTrigger id="setup-font" className="w-48">
                        <SelectValue placeholder="Font" />
                      </SelectTrigger>
                      <SelectContent>
                        {Object.entries(fonts).map(([key, f]) => (
                          <SelectItem
                            key={key}
                            value={key}
                            style={{ fontFamily: f.family }}
                          >
                            {f.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <code
                    className="setup-sample block text-2xl"
                    style={{ fontFamily: selectedFontFamily }}
                  >
                    {selectedFontLabel}
                  </code>
                  <div className="setup-glyph-box">
                    <code
                      className="setup-sample text-2xl"
                      style={{ fontFamily: selectedFontFamily }}
                    >
                      {FONT_GLYPH}
                    </code>
                  </div>
                </div>
              ) : null}

              {setupStep === 3 ? (
                <div className="flex items-center justify-between">
                  <Label htmlFor="setup-theme">Theme</Label>
                  <Select
                    value={setupTheme}
                    onValueChange={(v) => {
                      if (!v) return;
                      setSetupTheme(v);
                      saveConfig({ theme: v });
                    }}
                  >
                    <SelectTrigger id="setup-theme" className="w-48">
                      <SelectValue placeholder="Theme" />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(themes).map(([key, t]) => (
                        <SelectItem key={key} value={key}>
                          {t.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              ) : null}

              {setupStep < 3 ? (
                <ShimmerButton onClick={() => setSetupStep(setupStep + 1)}>
                  Next
                </ShimmerButton>
              ) : (
                <ShimmerButton onClick={() => setScreen("editor")}>Start coding</ShimmerButton>
              )}
            </CardContent>
          </Card>
        </div>
      </main>
    );
  }

  if (screen === "editor") {
    return (
      <main className="min-h-svh bg-background text-foreground">
        <div className="mx-auto flex max-w-5xl flex-col gap-6 p-8">
          <Card>
            <CardHeader>
              <CardTitle>Editor</CardTitle>
              <CardDescription>Your code, in a shadcn editor.</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <div className="flex gap-2">
                <ShimmerButton
                  onClick={async () => {
                    setRunAnswers([]);
                    const res = await fetch("/api/run", {
                      method: "POST",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({ code, answers: [] }),
                    });
                    const data = (await res.json()) as {
                      output: string;
                      error: string;
                      awaiting_answer: boolean;
                      stopped: boolean;
                      trace?: any;
                    };
                    setRunResult({
                      output: data.output ?? "",
                      error: data.error ?? "",
                      awaiting_answer: !!data.awaiting_answer,
                      stopped: !!data.stopped,
                    });
                    setTrace(data.trace || null);
                  }}
                >
                  Run
                </ShimmerButton>
                <Button
                  variant="outline"
                  onClick={() =>
                    fetch("/api/run/stop", {
                      method: "POST",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({}),
                    })
                  }
                >
                  Stop
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => {
                    const blob = new Blob([code], { type: "text/plain" });
                    const url = URL.createObjectURL(blob);
                    const link = document.createElement("a");
                    link.href = url;
                    link.download = "main.py";
                    link.click();
                    URL.revokeObjectURL(url);
                  }}
                >
                  Save
                </Button>
                <label className="inline-flex cursor-pointer items-center rounded-md border px-3 py-2 text-sm">
                  Open
                  <input
                    type="file"
                    accept=".py,.txt"
                    className="hidden"
                    onChange={async (e) => {
                      const file = e.target.files?.[0];
                      if (!file) return;
                      setCode(await file.text());
                    }}
                  />
                </label>
                <Button variant="outline" onClick={startShell}>
                  Shell
                </Button>
                <Button variant="outline" onClick={() => setShowTrace(true)} disabled={!trace?.available}>
                  Trace
                </Button>
                <Button variant="outline" onClick={() => setShowGlossary(true)}>
                  Glossary
                </Button>
              </div>
              <div className="flex flex-col gap-3">
                <div className="flex items-center justify-between">
                  <Label htmlFor="line-numbers">Line numbers</Label>
                  <Switch
                    id="line-numbers"
                    checked={config?.focus_mode !== "gutter"}
                    onCheckedChange={(v) =>
                      saveConfig({ focus_mode: v ? (config?.focus_mode === "lines" ? "lines" : "off") : "gutter" })
                    }
                  />
                </div>
                <div className="flex items-center justify-between">
                  <Label htmlFor="fade-lines">Fade other lines</Label>
                  <Switch
                    id="fade-lines"
                    checked={config?.focus_mode === "lines"}
                    onCheckedChange={(v) =>
                      saveConfig({ focus_mode: v ? "lines" : config?.focus_mode === "lines" ? "off" : config?.focus_mode || "off" })
                    }
                  />
                </div>
                {config?.focus_mode === "lines" ? (
                  <div className="flex items-center justify-between">
                    <Label htmlFor="blur-amount">Fade amount</Label>
                    <input
                      id="blur-amount"
                      type="range"
                      min={0}
                      max={1}
                      step={0.05}
                      value={config?.blur_intensity ?? 1}
                      onChange={(e) => saveConfig({ blur_intensity: Number(e.target.value) })}
                    />
                  </div>
                ) : null}
              </div>
              <div className="h-96 rounded-md border">
                <CodeMirror
                  value={code}
                  height="28rem"
                  basicSetup={{ lineNumbers: true }}
                  onChange={(v) => setCode(v)}
                  style={{ height: "100%" }}
                />
              </div>
              {shellOpen ? (
                <Card>
                  <CardHeader>
                    <CardTitle>Python shell</CardTitle>
                  </CardHeader>
                <CardContent className="flex flex-col gap-2">
                  <div className="flex gap-2">
                    <Button variant="outline" onClick={() => setShellOpen(false)}>
                      Close
                    </Button>
                    <Button variant="outline" onClick={() => setShellOutput("")}>
                      Clear
                    </Button>
                    <Button variant="outline" onClick={resetShell}>
                      Reset
                    </Button>
                    <Button variant="outline" onClick={stopShell}>
                      Stop
                    </Button>
                  </div>
                  <pre className="max-h-48 overflow-auto rounded-md bg-muted p-4 text-sm whitespace-pre-wrap">
                    {shellOutput || "Shell not started."}
                  </pre>
                  <div className="flex gap-2">
                    <input
                      className="flex-1 rounded-md border px-3 py-2"
                      value={shellInput}
                      onChange={(e) => setShellInput(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") runShell();
                      }}
                    />
                    <ShimmerButton onClick={runShell}>Run</ShimmerButton>
                  </div>
                </CardContent>
              </Card>
               ) : null}
              {showTrace ? (
                <Card>
                  <CardHeader>
                    <CardTitle>Trace</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <table className="w-full text-sm">
                      <thead>
                        <tr>
                          <th>Line</th>
                          <th>Variable</th>
                          <th>Value</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(trace?.rows || []).map((row: any, index: number) => (
                          <tr key={index}>
                            <td>{row.line}</td>
                            <td>{row.name}</td>
                            <td>{row.value}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    <Button variant="outline" onClick={() => setShowTrace(false)}>
                      Close
                    </Button>
                  </CardContent>
                </Card>
              ) : null}
              {showGlossary ? (
                <Card>
                  <CardHeader>
                    <CardTitle>Glossary</CardTitle>
                  </CardHeader>
                  <CardContent className="flex flex-col gap-4">
                    {glossary.map((section: any, index: number) => (
                      <div key={index}>
                        <h3 className="font-semibold">{section.title}</h3>
                        {section.note ? <p className="text-sm text-muted-foreground">{section.note}</p> : null}
                        <dl className="grid gap-1">
                          {section.rows.map((row: any, rowIndex: number) => (
                            <div key={rowIndex}>
                              <dt className="font-mono text-sm">{row.term}</dt>
                              <dd className="text-sm">{row.meaning}</dd>
                            </div>
                          ))}
                        </dl>
                      </div>
                    ))}
                    <Button variant="outline" onClick={() => setShowGlossary(false)}>
                      Close
                    </Button>
                  </CardContent>
                </Card>
              ) : null}
              {runResult ? (
                <Card>
                  <CardHeader>
                    <CardTitle>Output</CardTitle>
                  </CardHeader>
                  <CardContent className="flex flex-col gap-2">
                    {runResult.error ? (
                      <div role="alert" className="rounded-md border border-destructive bg-destructive/10 p-3">
                        <p className="text-sm text-destructive">{runResult.error}</p>
                      </div>
                    ) : null}
                    <pre className="max-h-48 overflow-auto rounded-md bg-muted p-4 text-sm whitespace-pre-wrap">
                      {runResult.output || "No output yet."}
                    </pre>
                    <div className="flex gap-2">
                      <Button variant="outline" onClick={clearOutput}>
                        Clear
                      </Button>
                    </div>
                    {runResult.awaiting_answer ? (
                      <form
                        className="flex gap-2"
                        onSubmit={(e) => {
                          e.preventDefault();
                          submitAnswer();
                        }}
                      >
                        <input
                          className="flex-1 rounded-md border px-3 py-2"
                          value={answerInput}
                          onChange={(e) => setAnswerInput(e.target.value)}
                        />
                        <Button type="submit">Send</Button>
                      </form>
                    ) : null}
                    {runResult.awaiting_answer ? (
                      <p className="text-sm text-muted-foreground">
                        The program is waiting for its next answer.
                      </p>
                    ) : null}
                    {runResult.stopped ? (
                      <p className="text-sm text-muted-foreground">Program stopped.</p>
                    ) : null}
                  </CardContent>
                </Card>
              ) : null}
            </CardContent>
          </Card>
        </div>
      </main>
    );
  }

  if (screen === "credits") {
    return (
      <main className="min-h-svh bg-background text-foreground">
        <div className="mx-auto flex max-w-3xl flex-col gap-6 p-8">
          <Card>
            <CardHeader>
              <CardTitle>Credits</CardTitle>
              <CardDescription>People and projects this app builds on.</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <ul className="flex flex-col gap-2">
                {credits.map((credit, index) => (
                  <li key={index} className="rounded-md bg-muted p-3">
                    {credit}
                  </li>
                ))}
              </ul>
              <Button variant="outline" onClick={() => setScreen("app")}>
                Back
              </Button>
            </CardContent>
          </Card>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-svh bg-background text-foreground">
      <div className="mx-auto flex max-w-5xl flex-col gap-6 p-8">
        <MagicCard className="w-full max-w-2xl p-8">
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, ease: "easeOut" }}
          >
            <Badge variant="secondary">shadcn</Badge>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight">
              AccessibleCoding
            </h1>
            <p className="text-muted-foreground">
              Accessible coding editor for dyslexic and neurodivergent learners.
            </p>
          </motion.div>
          <div className="mt-6 flex gap-2">
            <ShimmerButton onClick={() => setScreen("editor")}>Get started</ShimmerButton>
            <Button variant="outline" onClick={() => setScreen("credits")}>
              Credits
            </Button>
          </div>
        </MagicCard>

        <Card>
          <CardHeader>
            <CardTitle>Settings</CardTitle>
            <CardDescription>Every control in one shadcn screen.</CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="appearance">
              <TabsList>
                <TabsTrigger value="appearance">Appearance</TabsTrigger>
                <TabsTrigger value="reading">Reading</TabsTrigger>
                <TabsTrigger value="sound">Sound</TabsTrigger>
                <TabsTrigger value="speak">Speak</TabsTrigger>
                <TabsTrigger value="about">About</TabsTrigger>
                <TabsTrigger value="advanced">Advanced</TabsTrigger>
              </TabsList>
              <TabsContent value="appearance" className="mt-4">
                <div className="flex flex-col gap-4">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="theme">Theme</Label>
                    <Select
                      value={theme}
                      onValueChange={(v) => {
                        if (!v) return;
                        saveConfig({ theme: v });
                      }}
                    >
                      <SelectTrigger id="theme" className="w-48">
                        <SelectValue placeholder="Theme" />
                      </SelectTrigger>
                      <SelectContent>
                        {Object.entries(themes).map(([key, t]) => (
                          <SelectItem key={key} value={key}>
                            {t.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="flex flex-col gap-3">
                    <Label>Custom theme colours</Label>
                    {[
                      ["page", "Page"],
                      ["bg", "Background"],
                      ["fg", "Foreground"],
                      ["selection", "Selection"],
                      ["keyword", "Keyword"],
                      ["string", "String"],
                      ["comment", "Comment"],
                      ["number", "Number"],
                      ["function", "Function"],
                    ].map(([key, label]) => (
                      <div key={key} className="flex items-center justify-between gap-4">
                        <Label htmlFor={`theme-custom-${key}`}>{label}</Label>
                        <input
                          id={`theme-custom-${key}`}
                          type="color"
                          value={config?.[`theme_custom_${key}`] || "#000000"}
                          onChange={(e) => {
                            saveConfig({ [`theme_custom_${key}`]: e.target.value });
                            setCustomSaved(true);
                          }}
                        />
                      </div>
                    ))}
                    <Button
                      variant="outline"
                      onClick={() => saveConfig({ theme: "custom" })}
                    >
                      Use custom theme
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() =>
                        saveConfig({
                          theme_custom_page: "",
                          theme_custom_bg: "",
                          theme_custom_fg: "",
                          theme_custom_selection: "",
                          theme_custom_keyword: "",
                          theme_custom_string: "",
                          theme_custom_comment: "",
                          theme_custom_number: "",
                          theme_custom_function: "",
                        })
                      }
                    >
                      Reset custom colours
                    </Button>
                    {customSaved ? (
                      <p className="text-sm text-muted-foreground">Custom colours saved.</p>
                    ) : null}
                  </div>
                  <Button variant="outline" onClick={resetConfig}>
                    Reset all settings
                  </Button>
                </div>
              </TabsContent>
              <TabsContent value="reading" className="mt-4">
                <div className="flex flex-col gap-4">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="font">Reading font</Label>
                    <Select
                      value={font}
                      onValueChange={(v) => {
                        if (!v) return;
                        saveConfig({ font: v });
                      }}
                    >
                      <SelectTrigger id="font" className="w-48">
                        <SelectValue placeholder="Font" />
                      </SelectTrigger>
                      <SelectContent>
                        {Object.entries(fonts).map(([key, f]) => (
                          <SelectItem
                            key={key}
                            value={key}
                            style={{ fontFamily: f.family }}
                          >
                            {f.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <code
                    className="setup-sample block rounded-md bg-muted p-4 text-lg"
                    style={{ fontFamily: readingFontFamily }}
                  >
                    {FONT_GLYPH}
                  </code>
                  <div className="flex flex-col gap-2">
                    <Label htmlFor="font-upload">Upload a font</Label>
                    <input
                      id="font-upload"
                      type="file"
                      accept=".ttf,.otf,.woff,.woff2"
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) uploadFont(file);
                      }}
                    />
                    {fontUploadStatus ? (
                      <p className="text-sm text-muted-foreground">{fontUploadStatus}</p>
                    ) : null}
                    <div className="flex flex-col gap-2">
                      {Object.entries(fonts)
                        .filter(([, f]) => !(f as any).bundled)
                        .map(([key, f]) => (
                          <div key={key} className="flex items-center justify-between">
                            <span style={{ fontFamily: f.family }}>{f.name}</span>
                            <Button variant="outline" onClick={() => deleteFont(key)}>
                              Remove
                            </Button>
                          </div>
                        ))}
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <Label htmlFor="font-size">Text size</Label>
                    <input
                      id="font-size"
                      type="range"
                      min={12}
                      max={28}
                      value={config?.font_size ?? 16}
                      onChange={(e) => saveConfig({ font_size: Number(e.target.value) })}
                    />
                  </div>
                </div>
              </TabsContent>
              <TabsContent value="sound" className="mt-4">
                <div className="flex items-center justify-between">
                  <Label htmlFor="sound">Sound effects</Label>
                  <Switch
                    id="sound"
                    checked={sound}
                    onCheckedChange={(v) => saveConfig({ sound_enabled: v })}
                  />
                </div>
              </TabsContent>
              <TabsContent value="speak" className="mt-4">
                <div className="flex flex-col gap-4">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="speak">Speak Aloud</Label>
                    <Switch
                      id="speak"
                      checked={speak}
                      onCheckedChange={(v) => saveConfig({ tts_enabled: v })}
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <Label htmlFor="tts-engine">Voice engine</Label>
                    <Select
                      value={config?.tts_engine || "pyttsx3"}
                      onValueChange={(v) => {
                        if (v) saveConfig({ tts_engine: v });
                      }}
                    >
                      <SelectTrigger id="tts-engine" className="w-48">
                        <SelectValue placeholder="Engine" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="pyttsx3">pyttsx3</SelectItem>
                        <SelectItem value="gtts">gTTS</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="flex items-center justify-between">
                    <Label htmlFor="tts-gender">Voice</Label>
                    <Select
                      value={config?.tts_voice_gender || "any"}
                      onValueChange={(v) => {
                        if (v) saveConfig({ tts_voice_gender: v });
                      }}
                    >
                      <SelectTrigger id="tts-gender" className="w-48">
                        <SelectValue placeholder="Voice" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="any">Any</SelectItem>
                        <SelectItem value="male">Male</SelectItem>
                        <SelectItem value="female">Female</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="flex items-center justify-between">
                    <Label htmlFor="tts-rate">Rate</Label>
                    <input
                      id="tts-rate"
                      type="range"
                      min={0.5}
                      max={2}
                      step={0.1}
                      value={config?.tts_rate ?? 0.9}
                      onChange={(e) => saveConfig({ tts_rate: Number(e.target.value) })}
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <Label htmlFor="tts-voice">Voice</Label>
                    <input
                      id="tts-voice"
                      className="rounded-md border px-3 py-2"
                      value={config?.tts_voice || ""}
                      onChange={(e) => saveConfig({ tts_voice: e.target.value })}
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <Label htmlFor="tts-hover-delay">Hover delay</Label>
                    <input
                      id="tts-hover-delay"
                      type="range"
                      min={0}
                      max={2000}
                      step={50}
                      value={config?.tts_hover_delay ?? 600}
                      onChange={(e) => saveConfig({ tts_hover_delay: Number(e.target.value) })}
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <Label htmlFor="tts-hover-code">Hover code</Label>
                    <Switch
                      id="tts-hover-code"
                      checked={!!config?.tts_hover_code}
                      onCheckedChange={(v) => saveConfig({ tts_hover_code: v })}
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <Label htmlFor="tts-hover-output">Hover output</Label>
                    <Switch
                      id="tts-hover-output"
                      checked={!!config?.tts_hover_output}
                      onCheckedChange={(v) => saveConfig({ tts_hover_output: v })}
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <Label htmlFor="tts-hover-shell">Hover shell</Label>
                    <Switch
                      id="tts-hover-shell"
                      checked={!!config?.tts_hover_shell}
                      onCheckedChange={(v) => saveConfig({ tts_hover_shell: v })}
                    />
                  </div>
                </div>
              </TabsContent>
              <TabsContent value="about" className="mt-4">
                <div className="flex flex-col gap-2">
                  <Badge>Version {version}</Badge>
                  <p className="text-muted-foreground">
                    A free, open-source editor for learning Python. Your code
                    stays on this computer.
                  </p>
                  <Button variant="outline" onClick={() => setScreen("credits")}>
                    Credits
                  </Button>
                </div>
              </TabsContent>
              <TabsContent value="advanced" className="mt-4">
                <div className="flex flex-col gap-4">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="focus-mode">Focus mode</Label>
                    <Select
                      value={config?.focus_mode || "lines"}
                      onValueChange={(v) => v && saveConfig({ focus_mode: v })}
                    >
                      <SelectTrigger id="focus-mode" className="w-48">
                        <SelectValue placeholder="Focus" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="off">Off</SelectItem>
                        <SelectItem value="gutter">Gutter</SelectItem>
                        <SelectItem value="lines">Lines</SelectItem>
                        <SelectItem value="fade">Fade everything else</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="flex items-center justify-between">
                    <Label htmlFor="contrast">Contrast</Label>
                    <Select
                      value={config?.contrast || "normal"}
                      onValueChange={(v) => v && saveConfig({ contrast: v })}
                    >
                      <SelectTrigger id="contrast" className="w-48">
                        <SelectValue placeholder="Contrast" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="normal">Normal</SelectItem>
                        <SelectItem value="high">High</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="flex items-center justify-between">
                    <Label htmlFor="blur-intensity">Blur intensity</Label>
                    <input
                      id="blur-intensity"
                      type="range"
                      min={0}
                      max={1}
                      step={0.1}
                      value={config?.blur_intensity ?? 1}
                      onChange={(e) => saveConfig({ blur_intensity: Number(e.target.value) })}
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <Label htmlFor="reading-ruler">Reading ruler</Label>
                    <Switch
                      id="reading-ruler"
                      checked={!!config?.reading_ruler}
                      onCheckedChange={(v) => saveConfig({ reading_ruler: v })}
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <Label htmlFor="icon-only">Icon only buttons</Label>
                    <Switch
                      id="icon-only"
                      checked={!!config?.icon_only}
                      onCheckedChange={(v) => saveConfig({ icon_only: v })}
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <Label htmlFor="reduce-motion">Reduce motion</Label>
                    <Switch
                      id="reduce-motion"
                      checked={!!config?.reduce_motion}
                      onCheckedChange={(v) => saveConfig({ reduce_motion: v })}
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <Label htmlFor="glass-material">Glass material</Label>
                    <Select
                      value={config?.glass_material || "acrylic"}
                      onValueChange={(v) => v && saveConfig({ glass_material: v })}
                    >
                      <SelectTrigger id="glass-material" className="w-48">
                        <SelectValue placeholder="Glass" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="off">Off</SelectItem>
                        <SelectItem value="frosted">Frosted</SelectItem>
                        <SelectItem value="acrylic">Acrylic</SelectItem>
                        <SelectItem value="mica">Mica</SelectItem>
                        <SelectItem value="glossy">Glossy</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="flex items-center justify-between">
                    <Label htmlFor="tts-hover-scope">TTS hover scope</Label>
                    <Select
                      value={config?.tts_hover_scope || "all"}
                      onValueChange={(v) => v && saveConfig({ tts_hover_scope: v })}
                    >
                      <SelectTrigger id="tts-hover-scope" className="w-48">
                        <SelectValue placeholder="Scope" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="off">Off</SelectItem>
                        <SelectItem value="controls">Controls</SelectItem>
                        <SelectItem value="all">All</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="flex items-center justify-between">
                    <Label htmlFor="tts-click">Click to speak</Label>
                    <Switch
                      id="tts-click"
                      checked={!!config?.tts_click_to_speak}
                      onCheckedChange={(v) => saveConfig({ tts_click_to_speak: v })}
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <Label htmlFor="theme-gradient">Theme gradient</Label>
                    <Switch
                      id="theme-gradient"
                      checked={!!config?.theme_gradient}
                      onCheckedChange={(v) => saveConfig({ theme_gradient: v })}
                    />
                  </div>
                  <div className="flex flex-col gap-3">
                    <Label>Run and stop keys</Label>
                    <div className="flex items-center justify-between gap-4">
                      <Label htmlFor="run-key">Run key</Label>
                      <Select
                        value={runKey}
                        onValueChange={(v) => {
                          if (v) {
                            setRunKey(v);
                            saveConfig({ run_key: v });
                          }
                        }}
                      >
                        <SelectTrigger id="run-key" className="w-48">
                          <SelectValue placeholder="Run key" />
                        </SelectTrigger>
                        <SelectContent>
                          {RUN_KEYS.map((key) => (
                            <SelectItem key={key} value={key}>
                              {key}
                            </SelectItem>
                          ))}
                          {!RUN_KEYS.includes(runKey) ? (
                            <SelectItem value={runKey}>{runKey}</SelectItem>
                          ) : null}
                        </SelectContent>
                      </Select>
                      <Button
                        variant="outline"
                        onClick={() => setRecording("run")}
                      >
                        {recording === "run" ? "Press keys..." : "Record"}
                      </Button>
                    </div>
                    <div className="flex items-center justify-between gap-4">
                      <Label htmlFor="stop-key">Stop key</Label>
                      <Select
                        value={stopKey}
                        onValueChange={(v) => {
                          if (v) {
                            setStopKey(v);
                            saveConfig({ stop_key: v });
                          }
                        }}
                      >
                        <SelectTrigger id="stop-key" className="w-48">
                          <SelectValue placeholder="Stop key" />
                        </SelectTrigger>
                        <SelectContent>
                          {STOP_KEYS.map((key) => (
                            <SelectItem key={key} value={key}>
                              {key}
                            </SelectItem>
                          ))}
                          {!STOP_KEYS.includes(stopKey) ? (
                            <SelectItem value={stopKey}>{stopKey}</SelectItem>
                          ) : null}
                        </SelectContent>
                      </Select>
                      <Button
                        variant="outline"
                        onClick={() => setRecording("stop")}
                      >
                        {recording === "stop" ? "Press keys..." : "Record"}
                      </Button>
                    </div>
                    {recordingStatus ? (
                      <p className="text-sm text-muted-foreground">{recordingStatus}</p>
                    ) : null}
                  </div>

                  <div className="flex flex-col gap-3">
                    <Label>Updates</Label>
                    <div className="flex items-center justify-between">
                      <Label htmlFor="auto-update">Automatic checks</Label>
                      <Switch
                        id="auto-update"
                        checked={autoUpdate}
                        onCheckedChange={(v) => {
                          setAutoUpdate(v);
                          saveConfig({ auto_update: v });
                        }}
                      />
                    </div>
                    <div className="flex items-center justify-between">
                      <Label htmlFor="update-channel">Channel</Label>
                      <Select
                        value={updateChannel}
                        onValueChange={(v) => {
                          if (v) {
                            setUpdateChannel(v);
                            saveConfig({ update_channel: v });
                          }
                        }}
                      >
                        <SelectTrigger id="update-channel" className="w-48">
                          <SelectValue placeholder="Channel" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="beta">Beta</SelectItem>
                          <SelectItem value="stable">Stable</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="flex gap-2">
                      <Button variant="outline" onClick={checkUpdate}>
                        Check now
                      </Button>
                    </div>
                    {updateAvailable ? (
                      <div className="flex items-center justify-between gap-4">
                        <span>Install update</span>
                        <Button variant="outline" onClick={installUpdate}>
                          Install
                        </Button>
                      </div>
                    ) : null}
                    {updateInstalled ? (
                      <div className="flex items-center justify-between gap-4">
                        <span>Restart to apply</span>
                        <Button variant="outline" onClick={applyUpdate}>
                          Restart
                        </Button>
                      </div>
                    ) : null}
                    {updateStatus ? (
                      <p className="text-sm text-muted-foreground">{updateStatus}</p>
                    ) : null}
                    {updateInstalled ? (
                      <p className="text-sm text-muted-foreground">Downloaded update is ready to apply.</p>
                    ) : null}
                  </div>

                  <div className="flex flex-col gap-3">
                    <Label>Font areas</Label>
                    {[
                      ["font_in_code", "Code"],
                      ["font_in_output", "Output"],
                      ["font_in_shell", "Shell"],
                      ["font_in_ui", "Interface"],
                    ].map(([key, label]) => (
                      <div key={key} className="flex items-center justify-between">
                        <Label htmlFor={key}>{label}</Label>
                        <Switch
                          id={key}
                          checked={!!config?.[key]}
                          onCheckedChange={(v) => saveConfig({ [key]: v })}
                        />
                      </div>
                    ))}
                  </div>
                  <div className="flex items-center justify-between gap-4">
                    <Label htmlFor="highlight-color">Highlight colour</Label>
                    <input
                      id="highlight-color"
                      type="color"
                      value={config?.highlight_color || "#000000"}
                      onChange={(e) => saveConfig({ highlight_color: e.target.value })}
                    />
                  </div>
                  <div className="flex items-center justify-between gap-4">
                    <Label htmlFor="glass-tint">Glass tint</Label>
                    <input
                      id="glass-tint"
                      type="color"
                      value={config?.glass_tint || "#000000"}
                      onChange={(e) => saveConfig({ glass_tint: e.target.value })}
                    />
                  </div>
                  <Label>Pane text sizes</Label>
                  {([
                    ["editor_font_size", "Editor size", 12, 28],
                    ["editor_line_height", "Editor line height", 1, 2.4],
                    ["editor_letter_spacing", "Editor spacing", -0.5, 4],
                    ["output_font_size", "Output size", 12, 28],
                    ["output_line_height", "Output line height", 1, 2.4],
                    ["output_letter_spacing", "Output spacing", -0.5, 4],
                    ["shell_font_size", "Shell size", 12, 28],
                    ["shell_line_height", "Shell line height", 1, 2.4],
                    ["shell_letter_spacing", "Shell spacing", -0.5, 4],
                  ] as [string, string, number, number][]).map(([key, label, min, max]) => (
                    <div key={key} className="flex items-center justify-between gap-4">
                      <Label htmlFor={key}>{label}</Label>
                      <input
                        id={key}
                        type="range"
                        min={min}
                        max={max}
                        step={String(key).includes("spacing") ? 0.1 : String(key).includes("line") ? 0.1 : 1}
                        value={config?.[key] ?? (String(key).includes("size") ? 16 : String(key).includes("line") ? 1.6 : 0.5)}
                        onChange={(e) => saveConfig({ [key]: Number(e.target.value) })}
                      />
                    </div>
                  ))}
                  <Button variant="outline" onClick={resetConfig}>
                    Reset all settings
                  </Button>
                </div>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
