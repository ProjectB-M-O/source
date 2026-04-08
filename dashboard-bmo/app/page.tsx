"use client";

import { useState, useRef, useEffect } from "react";

// ── Constants ─────────────────────────────────────────────────────────────────

const API_URL = process.env.NEXT_PUBLIC_BMO_API_URL ?? "http://localhost:5271";

// ── Types ─────────────────────────────────────────────────────────────────────

type Message = {
    id: number;
    role: "user" | "ai" | "tool";
    text: string;
    time: string;
    toolName?: string;
    toolCallId?: string;
    toolResult?: string;
    audioUrl?: string;
};

type Skill = {
    name: string;
    description: string;
    file: string;
};

type BmoConfig = {
    version: string;
    workspace_path: string;
    dev_mode: boolean;
    services: {
        ai_brain: { port: number };
        bmo_api: { port: number };
        dashboard: { port: number };
        ai_voice: { enabled: boolean; port: number; audio_max_files: number };
    };
    agent: { name: string; model: string; max_tool_iterations: number };
    tools: { enabled: boolean; log_all: boolean; show_in_chat: boolean };
    context: { max_tokens: number; pruning_threshold: number; compaction_enabled: boolean };
};

// ── Icons ─────────────────────────────────────────────────────────────────────

function BmoIcon({ size = 20, color = "currentColor" }: { size?: number; color?: string }) {
    return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.8"
             strokeLinecap="round" strokeLinejoin="round">
            <rect x="2" y="3" width="20" height="14" rx="2"/>
            <path d="M8 21h8M12 17v4"/>
            <circle cx="9" cy="10" r="1.5" fill={color} stroke="none"/>
            <circle cx="15" cy="10" r="1.5" fill={color} stroke="none"/>
            <path d="M9 13.5c.8.7 2.4.7 3 0"/>
        </svg>
    );
}

function SendIcon() {
    return (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2"
             strokeLinecap="round" strokeLinejoin="round">
            <line x1="22" y1="2" x2="11" y2="13"/>
            <polygon points="22 2 15 22 11 13 2 9 22 2" fill="white" stroke="none"/>
        </svg>
    );
}

function SettingsIcon({ size = 20, color = "currentColor" }: { size?: number; color?: string }) {
    return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.8"
             strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="3"/>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
        </svg>
    );
}

function SkillsIcon({ size = 20, color = "currentColor" }: { size?: number; color?: string }) {
    return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.8"
             strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
        </svg>
    );
}

function WrenchIcon({ size = 14, color = "currentColor" }: { size?: number; color?: string }) {
    return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2"
             strokeLinecap="round" strokeLinejoin="round">
            <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>
        </svg>
    );
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function getTime() {
    return new Date().toLocaleTimeString("it-IT", { hour: "2-digit", minute: "2-digit" });
}

// ── Toggle ────────────────────────────────────────────────────────────────────

function Toggle({ value, onChange }: { value: boolean; onChange: (v: boolean) => void }) {
    return (
        <label style={{ position: "relative", display: "inline-block", width: "42px", height: "24px", cursor: "pointer", flexShrink: 0 }}>
            <input type="checkbox" checked={value} onChange={e => onChange(e.target.checked)}
                   style={{ opacity: 0, width: 0, height: 0, position: "absolute" }}/>
            <span style={{
                position: "absolute", inset: 0,
                background: value ? "var(--accent)" : "var(--surface)",
                border: `1px solid ${value ? "var(--accent)" : "var(--border)"}`,
                borderRadius: "24px",
                transition: "background 0.2s, border-color 0.2s",
            }}/>
            <span style={{
                position: "absolute",
                height: "18px", width: "18px",
                top: "2px",
                left: value ? "20px" : "2px",
                background: value ? "white" : "var(--text-muted)",
                borderRadius: "50%",
                transition: "left 0.18s, background 0.2s",
                pointerEvents: "none",
            }}/>
        </label>
    );
}

// ── Nav ───────────────────────────────────────────────────────────────────────

const NAV_ITEMS = [
    { id: "chat",     label: "Chat B.M.O.",   icon: BmoIcon },
    { id: "skills",   label: "Skills",        icon: SkillsIcon },
    { id: "settings", label: "Impostazioni",  icon: SettingsIcon },
] as const;

type ViewId = typeof NAV_ITEMS[number]["id"];

// ── Credential Row ────────────────────────────────────────────────────────────

function CredentialRow({ label, value, onChange, inputStyle }: {
    label: string; value: string; onChange: (v: string) => void;
    inputStyle: React.CSSProperties;
}) {
    const [show, setShow] = useState(false);
    return (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "16px", padding: "10px 0", borderBottom: "1px solid var(--border-subtle)" }}>
            <span style={{ fontSize: "13px", color: "var(--text-muted)", flexShrink: 0, fontFamily: "JetBrains Mono, monospace" }}>{label}</span>
            <div style={{ flex: 1, maxWidth: "260px", display: "flex", gap: "6px" }}>
                <input
                    type={show ? "text" : "password"}
                    style={{ ...inputStyle }}
                    value={value}
                    onChange={e => onChange(e.target.value)}
                />
                <button
                    onClick={() => setShow(s => !s)}
                    style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "6px", color: "var(--text-muted)", cursor: "pointer", padding: "4px 8px", fontSize: "11px", flexShrink: 0 }}
                >
                    {show ? "nascondi" : "mostra"}
                </button>
            </div>
        </div>
    );
}

// ── Settings View ─────────────────────────────────────────────────────────────

function SettingsView({ config, onSave }: { config: BmoConfig; onSave: (c: BmoConfig) => void }) {
    const [local, setLocal] = useState<BmoConfig>(JSON.parse(JSON.stringify(config)));
    const [saved, setSaved] = useState(false);
    const [saving, setSaving] = useState(false);
    const [envConfig, setEnvConfig] = useState<Record<string, string>>({});
    const [envSaved, setEnvSaved] = useState(false);
    const [envSaving, setEnvSaving] = useState(false);

    useEffect(() => {
        fetch(`${API_URL}/api/config/env`)
            .then(r => r.json())
            .then(setEnvConfig)
            .catch(() => {});
    }, []);

    function setAgent<K extends keyof BmoConfig["agent"]>(key: K, value: BmoConfig["agent"][K]) {
        setLocal(p => ({ ...p, agent: { ...p.agent, [key]: value } }));
    }
    function setTools<K extends keyof BmoConfig["tools"]>(key: K, value: BmoConfig["tools"][K]) {
        setLocal(p => ({ ...p, tools: { ...p.tools, [key]: value } }));
    }
    function setContext<K extends keyof BmoConfig["context"]>(key: K, value: BmoConfig["context"][K]) {
        setLocal(p => ({ ...p, context: { ...p.context, [key]: value } }));
    }
    function setAiVoice<K extends keyof BmoConfig["services"]["ai_voice"]>(key: K, value: BmoConfig["services"]["ai_voice"][K]) {
        setLocal(p => ({ ...p, services: { ...p.services, ai_voice: { ...p.services.ai_voice, [key]: value } } }));
    }

    async function handleSaveEnv() {
        setEnvSaving(true);
        try {
            const res = await fetch(`${API_URL}/api/config/env`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(envConfig),
            });
            if (res.ok) {
                setEnvSaved(true);
                setTimeout(() => setEnvSaved(false), 2500);
            }
        } finally {
            setEnvSaving(false);
        }
    }

    async function handleSave() {
        setSaving(true);
        try {
            const res = await fetch(`${API_URL}/api/config`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(local),
            });
            if (res.ok) {
                onSave(local);
                setSaved(true);
                setTimeout(() => setSaved(false), 2500);
            }
        } finally {
            setSaving(false);
        }
    }

    const inputStyle: React.CSSProperties = {
        background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "8px",
        color: "var(--text)", fontSize: "13px", padding: "7px 10px",
        fontFamily: "'Outfit', system-ui, sans-serif", outline: "none", width: "100%",
        transition: "border-color 0.2s",
    };

    function Row({ label, children }: { label: string; children: React.ReactNode }) {
        return (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "16px", padding: "10px 0", borderBottom: "1px solid var(--border-subtle)" }}>
                <span style={{ fontSize: "13px", color: "var(--text-muted)", flexShrink: 0 }}>{label}</span>
                <div style={{ flex: 1, maxWidth: "260px" }}>{children}</div>
            </div>
        );
    }

    function Section({ title }: { title: string }) {
        return (
            <div style={{ fontSize: "11px", fontWeight: 600, letterSpacing: "0.08em", color: "var(--accent)", textTransform: "uppercase", marginTop: "24px", marginBottom: "4px" }}>
                {title}
            </div>
        );
    }

    return (
        <div style={{ flex: 1, overflowY: "auto", padding: "28px 32px" }}>
            <div style={{ maxWidth: "560px" }}>
                <div style={{ fontWeight: 700, fontSize: "16px", color: "var(--text)", marginBottom: "4px" }}>Impostazioni</div>
                <div style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "8px" }}>
                    Modifica <code style={{ fontFamily: "JetBrains Mono, monospace", fontSize: "11px", color: "var(--accent)" }}>bmo_config.json</code>
                </div>

                <Section title="Sistema"/>
                <Row label="Dev mode (audio in chat)">
                    <Toggle value={local.dev_mode ?? true} onChange={v => setLocal(p => ({ ...p, dev_mode: v }))}/>
                </Row>

                <Section title="Agente"/>
                <Row label="Nome">
                    <input style={inputStyle} value={local.agent.name}
                           onChange={e => setAgent("name", e.target.value)}/>
                </Row>
                <Row label="Modello">
                    <input style={inputStyle} value={local.agent.model}
                           onChange={e => setAgent("model", e.target.value)}/>
                </Row>
                <Row label="Max iterazioni tool">
                    <input style={{ ...inputStyle, width: "80px" }} type="number" min={1} max={20}
                           value={local.agent.max_tool_iterations}
                           onChange={e => setAgent("max_tool_iterations", parseInt(e.target.value) || 1)}/>
                </Row>

                <Section title="Tool"/>
                <Row label="Tool abilitati">
                    <Toggle value={local.tools.enabled} onChange={v => setTools("enabled", v)}/>
                </Row>
                <Row label="Mostra tool calls in chat">
                    <Toggle value={local.tools.show_in_chat} onChange={v => setTools("show_in_chat", v)}/>
                </Row>
                <Row label="Log di tutti i tool">
                    <Toggle value={local.tools.log_all} onChange={v => setTools("log_all", v)}/>
                </Row>

                <Section title="Contesto"/>
                <Row label="Max token">
                    <input style={{ ...inputStyle, width: "100px" }} type="number" min={1000} step={500}
                           value={local.context.max_tokens}
                           onChange={e => setContext("max_tokens", parseInt(e.target.value) || 1000)}/>
                </Row>
                <Row label="Soglia pruning (0–1)">
                    <input style={{ ...inputStyle, width: "80px" }} type="number" min={0.1} max={1} step={0.1}
                           value={local.context.pruning_threshold}
                           onChange={e => setContext("pruning_threshold", parseFloat(e.target.value) || 0.8)}/>
                </Row>
                <Row label="Compaction automatica">
                    <Toggle value={local.context.compaction_enabled} onChange={v => setContext("compaction_enabled", v)}/>
                </Row>

                <Section title="Servizi (🔒 richiede restart)"/>
                <Row label="workspace_path">
                    <input style={{ ...inputStyle, opacity: 0.5, cursor: "not-allowed" }}
                           value={local.workspace_path ?? ""} disabled readOnly/>
                </Row>
                <Row label="Porta AI Brain">
                    <input style={{ ...inputStyle, width: "80px", opacity: 0.5, cursor: "not-allowed" }}
                           type="number" value={local.services?.ai_brain?.port ?? 8000} disabled readOnly/>
                </Row>
                <Row label="Porta Bmo API">
                    <input style={{ ...inputStyle, width: "80px", opacity: 0.5, cursor: "not-allowed" }}
                           type="number" value={local.services?.bmo_api?.port ?? 5271} disabled readOnly/>
                </Row>
                <Row label="Porta Dashboard">
                    <input style={{ ...inputStyle, width: "80px", opacity: 0.5, cursor: "not-allowed" }}
                           type="number" value={local.services?.dashboard?.port ?? 3000} disabled readOnly/>
                </Row>
                <Row label="Porta AI Voice">
                    <input style={{ ...inputStyle, width: "80px", opacity: 0.5, cursor: "not-allowed" }}
                           type="number" value={local.services?.ai_voice?.port ?? 5050} disabled readOnly/>
                </Row>

                <Section title="AI Voice"/>
                <Row label="Abilitato">
                    <Toggle value={local.services?.ai_voice?.enabled ?? false}
                            onChange={v => setAiVoice("enabled", v)}/>
                </Row>
                <Row label="Max file audio">
                    <input style={{ ...inputStyle, width: "80px" }} type="number" min={1} max={50}
                           value={local.services?.ai_voice?.audio_max_files ?? 10}
                           onChange={e => setAiVoice("audio_max_files", parseInt(e.target.value) || 1)}/>
                </Row>

                {/* Save */}
                <div style={{ marginTop: "28px", display: "flex", alignItems: "center", gap: "12px" }}>
                    <button onClick={handleSave} disabled={saving} style={{
                        padding: "9px 22px",
                        background: "linear-gradient(135deg, #2270c9 0%, #3b8eea 100%)",
                        border: "none", borderRadius: "10px", color: "white",
                        fontSize: "13px", fontWeight: 600, cursor: saving ? "not-allowed" : "pointer",
                        opacity: saving ? 0.6 : 1, transition: "opacity 0.2s",
                        fontFamily: "'Outfit', system-ui, sans-serif",
                    }}>
                        {saving ? "Salvataggio..." : "Salva"}
                    </button>
                    {saved && (
                        <span style={{ fontSize: "13px", color: "var(--online)" }}>✓ Salvato</span>
                    )}
                </div>

                {/* Credenziali */}
                <Section title="🔑 Credenziali (.env)"/>
                {Object.entries(envConfig).map(([key, value]) => (
                    <CredentialRow
                        key={key}
                        label={key}
                        value={value}
                        onChange={v => setEnvConfig(p => ({ ...p, [key]: v }))}
                        inputStyle={inputStyle}
                    />
                ))}
                {Object.keys(envConfig).length === 0 && (
                    <div style={{ fontSize: "12px", color: "var(--text-muted)", padding: "8px 0" }}>
                        File .env non trovato o vuoto.
                    </div>
                )}
                <div style={{ marginTop: "16px", display: "flex", alignItems: "center", gap: "12px" }}>
                    <button onClick={handleSaveEnv} disabled={envSaving} style={{
                        padding: "9px 22px",
                        background: "linear-gradient(135deg, #6b21a8 0%, #a78bfa 100%)",
                        border: "none", borderRadius: "10px", color: "white",
                        fontSize: "13px", fontWeight: 600, cursor: envSaving ? "not-allowed" : "pointer",
                        opacity: envSaving ? 0.6 : 1,
                        fontFamily: "'Outfit', system-ui, sans-serif",
                    }}>
                        {envSaving ? "Salvataggio..." : "Salva credenziali"}
                    </button>
                    {envSaved && <span style={{ fontSize: "13px", color: "var(--online)" }}>✓ Salvato</span>}
                </div>
            </div>
        </div>
    );
}

// ── Skills View ───────────────────────────────────────────────────────────────

function SkillsView() {
    const [skills, setSkills] = useState<Skill[]>([]);
    const [selected, setSelected] = useState<Skill | null>(null);
    const [content, setContent] = useState("");
    const [saving, setSaving] = useState(false);
    const [saved, setSaved] = useState(false);
    const [showModal, setShowModal] = useState(false);
    const [newName, setNewName] = useState("");
    const [newDesc, setNewDesc] = useState("");
    const [newFile, setNewFile] = useState("");
    const [loading, setLoading] = useState(true);
    const [loadingContent, setLoadingContent] = useState(false);

    // Dynamic import of Monaco to avoid SSR issues
    const [Editor, setEditor] = useState<React.ComponentType<{
        height: string; language: string; value: string;
        onChange: (v: string | undefined) => void; theme: string;
        options: object;
    }> | null>(null);

    useEffect(() => {
        import("@monaco-editor/react").then(mod => {
            setEditor(() => mod.default);
        });
    }, []);

    useEffect(() => {
        loadSkills();
    }, []);

    async function loadSkills() {
        setLoading(true);
        try {
            const r = await fetch(`${API_URL}/api/skills`);
            const data = await r.json();
            const list: Skill[] = data.capabilities ?? [];
            setSkills(list);
            if (list.length > 0 && !selected) {
                selectSkill(list[0]);
            }
        } catch {}
        setLoading(false);
    }

    async function selectSkill(skill: Skill) {
        setSelected(skill);
        setLoadingContent(true);
        try {
            const filename = skill.file.split("/").pop() ?? skill.file;
            const r = await fetch(`${API_URL}/api/skills/content?file=${encodeURIComponent(filename)}`);
            const data = await r.json();
            setContent(data.content ?? "");
        } catch {
            setContent("");
        }
        setLoadingContent(false);
    }

    async function handleSave() {
        if (!selected) return;
        setSaving(true);
        try {
            const filename = selected.file.split("/").pop() ?? selected.file;
            const r = await fetch(`${API_URL}/api/skills/content?file=${encodeURIComponent(filename)}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ content }),
            });
            if (r.ok) { setSaved(true); setTimeout(() => setSaved(false), 2500); }
        } finally { setSaving(false); }
    }

    async function handleCreate() {
        if (!newName.trim() || !newFile.trim()) return;
        const filename = newFile.trim().endsWith(".md") ? newFile.trim() : newFile.trim() + ".md";
        try {
            const r = await fetch(`${API_URL}/api/skills`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name: newName, description: newDesc, filename }),
            });
            if (r.ok) {
                setShowModal(false);
                setNewName(""); setNewDesc(""); setNewFile("");
                // Reload skills, then select the newly created one
                const skillsRes = await fetch(`${API_URL}/api/skills`);
                if (skillsRes.ok) {
                    const data = await skillsRes.json();
                    const list: Skill[] = data.capabilities ?? [];
                    setSkills(list);
                    const created = list.find(s => s.file === `skills/${filename}`);
                    if (created) selectSkill(created);
                }
            }
        } catch {}
    }

    const inputStyle: React.CSSProperties = {
        background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "8px",
        color: "var(--text)", fontSize: "13px", padding: "7px 10px",
        fontFamily: "'Outfit', system-ui, sans-serif", outline: "none", width: "100%",
    };

    return (
        <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
            {/* Left panel: skill list */}
            <div style={{
                width: "240px", flexShrink: 0, borderRight: "1px solid var(--border)",
                display: "flex", flexDirection: "column", background: "var(--sidebar-bg)",
            }}>
                <div style={{ padding: "20px 16px 12px", borderBottom: "1px solid var(--border)" }}>
                    <div style={{ fontWeight: 700, fontSize: "14px", color: "var(--text)", marginBottom: "10px" }}>Skills</div>
                    <button onClick={() => setShowModal(true)} style={{
                        width: "100%", padding: "8px 12px",
                        background: "linear-gradient(135deg, #2270c9 0%, #3b8eea 100%)",
                        border: "none", borderRadius: "8px", color: "white",
                        fontSize: "12px", fontWeight: 600, cursor: "pointer",
                        fontFamily: "'Outfit', system-ui, sans-serif",
                    }}>
                        ＋ Nuova Skill
                    </button>
                </div>
                <div style={{ flex: 1, overflowY: "auto", padding: "8px 0" }}>
                    {loading ? (
                        <div style={{ padding: "16px", fontSize: "12px", color: "var(--text-muted)" }}>Caricamento...</div>
                    ) : skills.map(skill => (
                        <div key={skill.file} onClick={() => selectSkill(skill)} style={{
                            padding: "10px 16px", cursor: "pointer",
                            background: selected?.file === skill.file ? "var(--surface-hover)" : "transparent",
                            borderLeft: selected?.file === skill.file ? "2px solid var(--accent)" : "2px solid transparent",
                            transition: "background 0.15s",
                        }}>
                            <div style={{ fontSize: "13px", fontWeight: 500, color: "var(--text)" }}>{skill.name}</div>
                            <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "2px" }}>{skill.description}</div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Right panel: Monaco editor */}
            <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
                {selected ? (
                    <>
                        <div style={{
                            padding: "10px 20px", background: "var(--sidebar-bg)",
                            borderBottom: "1px solid var(--border)",
                            display: "flex", alignItems: "center", justifyContent: "space-between",
                        }}>
                            <div>
                                <span style={{ fontWeight: 600, fontSize: "14px", color: "var(--text)" }}>{selected.name}</span>
                                <span style={{ marginLeft: "8px", fontSize: "11px", color: "var(--text-muted)", fontFamily: "JetBrains Mono, monospace" }}>{selected.file}</span>
                            </div>
                            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                                {saved && <span style={{ fontSize: "12px", color: "var(--online)" }}>✓ Salvato</span>}
                                <button onClick={handleSave} disabled={saving} style={{
                                    padding: "7px 18px",
                                    background: "linear-gradient(135deg, #2270c9 0%, #3b8eea 100%)",
                                    border: "none", borderRadius: "8px", color: "white",
                                    fontSize: "12px", fontWeight: 600, cursor: saving ? "not-allowed" : "pointer",
                                    opacity: saving ? 0.6 : 1,
                                    fontFamily: "'Outfit', system-ui, sans-serif",
                                }}>
                                    {saving ? "Salvataggio..." : "Salva"}
                                </button>
                            </div>
                        </div>
                        <div style={{ flex: 1, overflow: "hidden" }}>
                            {loadingContent ? (
                                <div style={{ padding: "20px", fontSize: "13px", color: "var(--text-muted)" }}>Caricamento...</div>
                            ) : Editor ? (
                                <Editor
                                    height="100%"
                                    language="markdown"
                                    value={content}
                                    onChange={v => setContent(v ?? "")}
                                    theme="vs-dark"
                                    options={{
                                        minimap: { enabled: false },
                                        fontSize: 14,
                                        lineNumbers: "off",
                                        wordWrap: "on",
                                        scrollBeyondLastLine: false,
                                        renderLineHighlight: "none",
                                        fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                                    }}
                                />
                            ) : (
                                <div style={{ padding: "20px", fontSize: "13px", color: "var(--text-muted)" }}>Caricamento editor...</div>
                            )}
                        </div>
                    </>
                ) : (
                    <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-muted)", fontSize: "13px" }}>
                        Seleziona una skill
                    </div>
                )}
            </div>

            {/* Modal: nuova skill */}
            {showModal && (
                <div style={{
                    position: "fixed", inset: 0,
                    background: "rgba(0,0,0,0.6)", backdropFilter: "blur(4px)",
                    display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000,
                }}>
                    <div style={{
                        background: "var(--sidebar-bg)", border: "1px solid var(--border)",
                        borderRadius: "16px", padding: "28px", width: "360px",
                        boxShadow: "0 20px 60px rgba(0,0,0,0.5)",
                    }}>
                        <div style={{ fontWeight: 700, fontSize: "15px", color: "var(--text)", marginBottom: "20px" }}>Nuova Skill</div>
                        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                            <div>
                                <div style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "4px" }}>Nome *</div>
                                <input style={inputStyle} value={newName} onChange={e => setNewName(e.target.value)} placeholder="es. Web Search"/>
                            </div>
                            <div>
                                <div style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "4px" }}>Descrizione</div>
                                <input style={inputStyle} value={newDesc} onChange={e => setNewDesc(e.target.value)} placeholder="Breve descrizione della skill"/>
                            </div>
                            <div>
                                <div style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "4px" }}>Nome file (.md) *</div>
                                <input style={inputStyle} value={newFile} onChange={e => setNewFile(e.target.value)} placeholder="es. web_search.md"/>
                            </div>
                        </div>
                        <div style={{ display: "flex", gap: "10px", marginTop: "24px", justifyContent: "flex-end" }}>
                            <button onClick={() => setShowModal(false)} style={{
                                padding: "8px 18px", background: "var(--surface)",
                                border: "1px solid var(--border)", borderRadius: "8px",
                                color: "var(--text-muted)", fontSize: "13px", cursor: "pointer",
                                fontFamily: "'Outfit', system-ui, sans-serif",
                            }}>Annulla</button>
                            <button onClick={handleCreate} disabled={!newName.trim() || !newFile.trim()} style={{
                                padding: "8px 18px",
                                background: "linear-gradient(135deg, #2270c9 0%, #3b8eea 100%)",
                                border: "none", borderRadius: "8px", color: "white",
                                fontSize: "13px", fontWeight: 600,
                                cursor: (!newName.trim() || !newFile.trim()) ? "not-allowed" : "pointer",
                                opacity: (!newName.trim() || !newFile.trim()) ? 0.5 : 1,
                                fontFamily: "'Outfit', system-ui, sans-serif",
                            }}>Crea</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

// ── Main Component ────────────────────────────────────────────────────────────

export default function Home() {
    const [view, setView] = useState<ViewId>("chat");
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [isOnline, setIsOnline] = useState(false);
    const [config, setConfig] = useState<BmoConfig | null>(null);
    const [ttsEnabled, setTtsEnabled] = useState(false);
    const audioUrlsRef = useRef<string[]>([]);
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Carica config all'avvio
    useEffect(() => {
        fetch(`${API_URL}/api/config`)
            .then(r => r.json())
            .then(setConfig)
            .catch(() => {});
    }, []);

    // Load conversation history on mount
    useEffect(() => {
        fetch(`${API_URL}/api/chat/history`)
            .then(r => r.ok ? r.json() : null)
            .then(data => {
                if (!data?.messages?.length) return;
                const loaded: Message[] = data.messages.map((m: {role: string; content: string; created_at: string}, i: number) => ({
                    id: i + 1,
                    role: m.role === "assistant" ? "ai" as const : "user" as const,
                    text: m.content,
                    time: new Date(m.created_at).toLocaleTimeString("it-IT", { hour: "2-digit", minute: "2-digit" }),
                }));
                setMessages(loaded);
            })
            .catch(() => {});
    }, []);

    // Health check ogni 10s
    useEffect(() => {
        const check = async () => {
            try {
                const r = await fetch(`${API_URL}/api/health`);
                setIsOnline(r.ok);
            } catch {
                setIsOnline(false);
            }
        };
        check();
        const id = setInterval(check, 10000);
        return () => clearInterval(id);
    }, []);

    // Scroll to bottom
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    // ── Audio helpers ────────────────────────────────────────────────────────

    function b64ToUrl(b64: string): string {
        const binary = atob(b64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
        const blob = new Blob([bytes], { type: "audio/wav" });
        const url = URL.createObjectURL(blob);
        // FIFO: max 10 blob URLs in memoria
        audioUrlsRef.current.push(url);
        if (audioUrlsRef.current.length > 10) {
            const old = audioUrlsRef.current.shift()!;
            URL.revokeObjectURL(old);
        }
        return url;
    }

    // ── Send ────────────────────────────────────────────────────────────────

    async function handleSend() {
        const text = input.trim();
        if (!text || loading) return;

        // Comando /new
        if (text === "/new") {
            setInput("");
            try {
                await fetch(`${API_URL}/api/chat/reset`, { method: "POST" });
            } catch { /* ignore */ }
            setMessages([{
                id: Date.now(), role: "ai",
                text: "Sessione riavviata. Come posso aiutarti?",
                time: getTime(),
            }]);
            return;
        }

        setMessages(prev => [...prev, { id: Date.now(), role: "user", text, time: getTime() }]);
        setInput("");
        if (textareaRef.current) {
            textareaRef.current.style.height = "auto";
        }
        setLoading(true);

        const showTools = config?.tools?.show_in_chat !== false;

        try {
            const res = await fetch(`${API_URL}/api/chat/stream`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: text, tts: ttsEnabled && (config?.dev_mode ?? false) }),
                cache: "no-store",
            });

            if (!res.ok || !res.body) throw new Error(`Errore ${res.status}`);

            const reader  = res.body.getReader();
            const decoder = new TextDecoder();
            let buffer     = "";
            let aiMsgId    = Date.now() + 1;
            let aiCreated  = false;

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const parts = buffer.split("\n\n");
                buffer = parts.pop() ?? "";

                for (const part of parts) {
                    const line = part.trim();
                    if (!line.startsWith("data: ")) continue;
                    const raw = line.slice(6).trim();
                    if (!raw) continue;

                    let event: Record<string, unknown>;
                    try { event = JSON.parse(raw); }
                    catch { continue; }

                    switch (event.type) {
                        case "delta": {
                            if (!aiCreated) {
                                setMessages(prev => [...prev, { id: aiMsgId, role: "ai", text: "", time: getTime() }]);
                                aiCreated = true;
                            }
                            setMessages(prev => prev.map(m =>
                                m.id === aiMsgId ? { ...m, text: m.text + (event.content as string) } : m
                            ));
                            break;
                        }
                        case "tool_call": {
                            if (!showTools) break;
                            setMessages(prev => [...prev, {
                                id: Date.now() + Math.random(),
                                role: "tool",
                                text: JSON.stringify(event.args, null, 2),
                                time: getTime(),
                                toolName: event.name as string,
                                toolCallId: event.id as string,
                            }]);
                            break;
                        }
                        case "tool_result": {
                            if (!showTools) break;
                            setMessages(prev => {
                                const updated = [...prev];
                                const idx = updated.findLastIndex(
                                    m => m.role === "tool" && m.toolCallId === (event.id as string)
                                );
                                if (idx !== -1) {
                                    updated[idx] = { ...updated[idx], toolResult: event.result as string };
                                }
                                return updated;
                            });
                            break;
                        }
                        case "audio": {
                            const url = b64ToUrl(event.data as string);
                            setMessages(prev => prev.map(m =>
                                m.id === aiMsgId ? { ...m, audioUrl: url } : m
                            ));
                            break;
                        }
                        case "done":
                            break;
                    }
                }
            }
        } catch (e) {
            setMessages(prev => [...prev, {
                id: Date.now(), role: "ai",
                text: e instanceof Error ? e.message : String(e),
                time: getTime(),
            }]);
        } finally {
            setLoading(false);
        }
    }

    function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    }

    function handleInput(e: React.FormEvent<HTMLTextAreaElement>) {
        const el = e.currentTarget;
        el.style.height = "auto";
        el.style.height = Math.min(el.scrollHeight, 140) + "px";
    }

    // ── Render ───────────────────────────────────────────────────────────────

    return (
        <div style={{ display: "flex", height: "100vh", overflow: "hidden" }}>

            {/* ── Sidebar ── */}
            <aside style={{
                width: "260px", flexShrink: 0,
                background: "var(--sidebar-bg)",
                borderRight: "1px solid var(--border)",
                display: "flex", flexDirection: "column",
            }}>
                {/* Logo */}
                <div style={{
                    padding: "16px", borderBottom: "1px solid var(--border)",
                    display: "flex", alignItems: "center", gap: "10px",
                }}>
                    <div style={{
                        width: "34px", height: "34px", borderRadius: "10px",
                        background: "linear-gradient(135deg, #2270c9 0%, #3b8eea 100%)",
                        display: "flex", alignItems: "center", justifyContent: "center",
                        flexShrink: 0, boxShadow: "0 2px 12px rgba(59,142,234,0.3)",
                    }}>
                        <BmoIcon size={17} color="white"/>
                    </div>
                    <div>
                        <div style={{ fontWeight: 700, fontSize: "14px", letterSpacing: "0.04em", color: "var(--text)" }}>B.M.O.</div>
                        <div style={{ fontSize: "11px", color: "var(--text-muted)", letterSpacing: "0.02em" }}>AI Dashboard</div>
                    </div>
                </div>

                {/* Nav */}
                <nav style={{ padding: "6px 0", flex: 1 }}>
                    {NAV_ITEMS.map(item => {
                        const active = view === item.id;
                        return (
                            <div key={item.id} className="nav-item" onClick={() => setView(item.id)} style={{
                                display: "flex", alignItems: "center", gap: "11px",
                                padding: "9px 14px", cursor: "pointer",
                                background: active ? "var(--surface-hover)" : "transparent",
                                borderLeft: active ? "2px solid var(--accent)" : "2px solid transparent",
                            }}>
                                <div style={{
                                    width: "36px", height: "36px", borderRadius: "50%",
                                    background: active ? "linear-gradient(135deg, #2270c9 0%, #3b8eea 100%)" : "var(--surface)",
                                    display: "flex", alignItems: "center", justifyContent: "center",
                                    flexShrink: 0, boxShadow: active ? "0 2px 10px rgba(59,142,234,0.25)" : "none",
                                }}>
                                    <item.icon size={17} color={active ? "white" : "var(--text-muted)"}/>
                                </div>
                                <span style={{
                                    fontWeight: 500, fontSize: "13.5px",
                                    color: active ? "var(--text)" : "var(--text-muted)",
                                }}>
                                    {item.label}
                                </span>
                            </div>
                        );
                    })}
                </nav>
            </aside>

            {/* ── Content ── */}
            {view === "settings" ? (
                config
                    ? <SettingsView config={config} onSave={setConfig}/>
                    : (
                        <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-muted)", fontSize: "13px" }}>
                            Caricamento impostazioni...
                        </div>
                    )
            ) : view === "skills" ? (
                <SkillsView />
            ) : (
                <main style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", background: "var(--chat-bg)" }}>

                    {/* Chat header */}
                    <div style={{
                        padding: "10px 20px", background: "var(--sidebar-bg)",
                        borderBottom: "1px solid var(--border)",
                        display: "flex", alignItems: "center", gap: "12px",
                    }}>
                        <div style={{
                            width: "36px", height: "36px", borderRadius: "50%",
                            background: "linear-gradient(135deg, #2270c9 0%, #3b8eea 100%)",
                            display: "flex", alignItems: "center", justifyContent: "center",
                            flexShrink: 0, boxShadow: "0 2px 10px rgba(59,142,234,0.25)",
                        }}>
                            <BmoIcon size={17} color="white"/>
                        </div>
                        <div>
                            <div style={{ fontWeight: 600, fontSize: "14.5px", color: "var(--text)", letterSpacing: "0.01em" }}>
                                B.M.O.
                            </div>
                            <div style={{ fontSize: "11.5px", color: isOnline ? "var(--online)" : "var(--offline)", display: "flex", alignItems: "center", gap: "4px" }}>
                                <span style={{
                                    display: "inline-block", width: "6px", height: "6px",
                                    borderRadius: "50%", background: isOnline ? "var(--online)" : "var(--offline)",
                                }}/>
                                {isOnline ? "online" : "offline"}
                            </div>
                        </div>
                    </div>

                    {/* Messages */}
                    <div style={{ flex: 1, overflowY: "auto", padding: "20px 24px", display: "flex", flexDirection: "column", gap: "4px" }}>
                        {messages.length === 0 && (
                            <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: "14px" }}>
                                <div style={{
                                    width: "56px", height: "56px", borderRadius: "18px",
                                    background: "var(--surface)", border: "1px solid var(--border)",
                                    display: "flex", alignItems: "center", justifyContent: "center",
                                    boxShadow: "0 0 30px rgba(59,142,234,0.06)",
                                }}>
                                    <BmoIcon size={28} color="var(--accent)"/>
                                </div>
                                <span style={{ color: "var(--text-muted)", fontSize: "13px", letterSpacing: "0.02em" }}>
                                    Come posso aiutarti?
                                </span>
                                <span style={{ color: "var(--text-muted)", fontSize: "11px", opacity: 0.5 }}>
                                    Digita /new per iniziare una nuova sessione
                                </span>
                            </div>
                        )}

                        {messages.map((msg, i) => {
                            const isUser = msg.role === "user";
                            const isTool = msg.role === "tool";
                            const prevSame = i > 0 && messages[i - 1].role === msg.role;

                            if (isTool) {
                                return (
                                    <div key={msg.id} className="msg-bubble" style={{
                                        marginTop: prevSame ? "2px" : "10px",
                                        alignSelf: "flex-start",
                                        maxWidth: "70%",
                                    }}>
                                        <div style={{
                                            background: "var(--bubble-tool)",
                                            border: "1px solid var(--border-tool)",
                                            borderLeft: "3px solid var(--accent-tool)",
                                            borderRadius: "12px",
                                            padding: "8px 12px",
                                            fontSize: "12px",
                                        }}>
                                            {/* Header */}
                                            <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "6px" }}>
                                                <WrenchIcon size={13} color="var(--accent-tool)"/>
                                                <span style={{ color: "var(--accent-tool)", fontWeight: 600, fontFamily: "'JetBrains Mono', monospace" }}>
                                                    {msg.toolName}
                                                </span>
                                                <span style={{ marginLeft: "auto", fontSize: "10.5px", color: "var(--text-muted)" }}>{msg.time}</span>
                                            </div>
                                            {/* Args */}
                                            {msg.text && msg.text !== "{}" && (
                                                <pre style={{
                                                    margin: 0, marginBottom: msg.toolResult ? "6px" : 0,
                                                    color: "var(--text-bubble-tool)", fontSize: "11px",
                                                    fontFamily: "'JetBrains Mono', monospace",
                                                    whiteSpace: "pre-wrap", wordBreak: "break-word",
                                                    opacity: 0.85,
                                                }}>
                                                    {msg.text}
                                                </pre>
                                            )}
                                            {/* Result */}
                                            {msg.toolResult !== undefined && (
                                                <div style={{
                                                    borderTop: "1px solid var(--border-tool)",
                                                    paddingTop: "5px",
                                                    color: msg.toolResult.startsWith("[Errore")
                                                        ? "var(--offline)"
                                                        : "var(--online)",
                                                    fontSize: "11px",
                                                    fontFamily: "'JetBrains Mono', monospace",
                                                    whiteSpace: "pre-wrap", wordBreak: "break-word",
                                                }}>
                                                    {msg.toolResult.startsWith("[Errore") ? "✗ " : "✓ "}
                                                    {msg.toolResult}
                                                </div>
                                            )}
                                            {/* Loading indicator while waiting for result */}
                                            {msg.toolResult === undefined && (
                                                <div style={{ color: "var(--text-muted)", fontSize: "11px", fontStyle: "italic" }}>
                                                    esecuzione...
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                );
                            }

                            return (
                                <div key={msg.id} style={{
                                    display: "flex",
                                    justifyContent: isUser ? "flex-end" : "flex-start",
                                    marginTop: prevSame ? "2px" : "10px",
                                }}>
                                    <div className="msg-bubble" style={{
                                        maxWidth: "65%",
                                        padding: "8px 13px 7px",
                                        borderRadius: isUser ? "18px 18px 4px 18px" : "18px 18px 18px 4px",
                                        background: isUser ? "var(--bubble-user)" : "var(--bubble-ai)",
                                        color: isUser ? "var(--text-bubble-user)" : "var(--text-bubble-ai)",
                                        fontSize: "14px", lineHeight: "1.55", wordBreak: "break-word",
                                        border: isUser ? "1px solid rgba(59,142,234,0.2)" : "1px solid var(--border)",
                                        boxShadow: isUser ? "0 2px 14px rgba(59,142,234,0.12)" : "0 2px 8px rgba(0,0,0,0.35)",
                                    }}>
                                        <span>{msg.text}</span>
                                        {loading && !isUser && i === messages.length - 1 && msg.text === "" && (
                                            <span style={{ color: "var(--text-muted)", animation: "pulse 1s infinite" }}>▌</span>
                                        )}
                                        {!isUser && msg.audioUrl && (
                                            <div style={{ marginTop: "6px" }}>
                                                <audio
                                                    controls
                                                    src={msg.audioUrl}
                                                    style={{ height: "32px", width: "100%", maxWidth: "260px", borderRadius: "16px" }}
                                                />
                                            </div>
                                        )}
                                        <span style={{
                                            display: "inline-block", marginLeft: "8px",
                                            fontSize: "10.5px", fontFamily: "'JetBrains Mono', monospace",
                                            color: isUser ? "var(--text-time-user)" : "var(--text-time-ai)",
                                            verticalAlign: "bottom", whiteSpace: "nowrap",
                                        }}>
                                            {msg.time}
                                        </span>
                                    </div>
                                </div>
                            );
                        })}

                        {/* Loading dots when no AI message yet */}
                        {loading && !messages.some((m, i) => m.role === "ai" && i === messages.length - 1) && (
                            <div style={{ display: "flex", justifyContent: "flex-start", marginTop: "10px" }}>
                                <div style={{
                                    padding: "10px 14px",
                                    background: "var(--bubble-ai)", border: "1px solid var(--border)",
                                    borderRadius: "18px 18px 18px 4px",
                                    display: "flex", gap: "4px", alignItems: "center",
                                }}>
                                    {[0, 1, 2].map(i => (
                                        <span key={i} style={{
                                            width: "5px", height: "5px", borderRadius: "50%",
                                            background: "var(--text-muted)",
                                            animation: `pulse 1.2s ease-in-out ${i * 0.2}s infinite`,
                                        }}/>
                                    ))}
                                </div>
                            </div>
                        )}
                        <div ref={messagesEndRef}/>
                    </div>

                    {/* Input */}
                    <div style={{
                        padding: "12px 16px 14px", background: "var(--sidebar-bg)",
                        borderTop: "1px solid var(--border)",
                        display: "flex", alignItems: "flex-end", gap: "10px",
                    }}>
                        {/* TTS toggle — visibile solo in dev_mode */}
                        {config?.dev_mode && (
                            <div style={{
                                display: "flex", alignItems: "center", gap: "6px",
                                flexShrink: 0, paddingBottom: "10px",
                            }}>
                                <Toggle value={ttsEnabled} onChange={setTtsEnabled}/>
                                <span style={{
                                    fontSize: "14px",
                                    color: ttsEnabled ? "var(--accent)" : "var(--text-muted)",
                                    whiteSpace: "nowrap",
                                    cursor: "pointer",
                                }} title={ttsEnabled ? "Risposta vocale attiva" : "Risposta vocale disattiva"}
                                onClick={() => setTtsEnabled(v => !v)}>
                                    🔊
                                </span>
                            </div>
                        )}
                        <div className="input-wrapper" style={{
                            flex: 1, background: "var(--surface)", borderRadius: "22px",
                            padding: "10px 16px", display: "flex", alignItems: "flex-end",
                            border: "1px solid var(--border)",
                        }}>
                            <textarea
                                ref={textareaRef}
                                value={input}
                                onChange={e => setInput(e.target.value)}
                                onKeyDown={handleKeyDown}
                                onInput={handleInput}
                                placeholder="Scrivi un messaggio... (/new per nuova sessione)"
                                rows={1}
                                disabled={loading}
                                style={{
                                    flex: 1, background: "transparent", border: "none", outline: "none",
                                    resize: "none", color: "var(--text)", fontSize: "14px",
                                    lineHeight: "1.5", maxHeight: "140px",
                                    fontFamily: "'Outfit', system-ui, sans-serif",
                                }}
                            />
                        </div>
                        <button
                            className="send-btn"
                            onClick={handleSend}
                            disabled={!input.trim() || loading}
                            style={{
                                width: "42px", height: "42px", borderRadius: "50%",
                                background: input.trim() && !loading
                                    ? "linear-gradient(135deg, #2270c9 0%, #3b8eea 100%)"
                                    : "var(--surface)",
                                border: "1px solid " + (input.trim() && !loading ? "transparent" : "var(--border)"),
                                cursor: input.trim() && !loading ? "pointer" : "default",
                                display: "flex", alignItems: "center", justifyContent: "center",
                                flexShrink: 0,
                            }}
                        >
                            <SendIcon/>
                        </button>
                    </div>
                </main>
            )}
        </div>
    );
}
