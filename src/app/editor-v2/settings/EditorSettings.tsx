"use client";

type EditorSettingsProps = {
    open: boolean;
    fontSize: number;
    wordWrap: boolean;
    autoCompile: boolean;
    compileDelayMs: number;
    theme: "light" | "dark";
    onClose: () => void;
    onSave: (prefs: {
        fontSize: number;
        wordWrap: boolean;
        autoCompile: boolean;
        compileDelayMs: number;
        theme: "light" | "dark";
    }) => void;
};

export default function EditorSettings({
    open,
    fontSize,
    wordWrap,
    autoCompile,
    compileDelayMs,
    theme,
    onClose,
    onSave,
}: EditorSettingsProps) {
    if (!open) return null;
    return (
        <div
            style={{
                position: "fixed",
                inset: 0,
                background: "rgba(0,0,0,0.35)",
                zIndex: 1200,
                display: "grid",
                placeItems: "center",
            }}
            onClick={onClose}
        >
            <div
                style={{ width: "min(560px, 92vw)", background: "#fff", borderRadius: "10px", padding: "1rem" }}
                onClick={(e) => e.stopPropagation()}
            >
                <h3 style={{ marginBottom: "0.8rem" }}>Editor Settings</h3>
                <div style={{ display: "grid", gap: "0.7rem" }}>
                    <label>
                        Font Size: <strong>{fontSize}px</strong>
                        <input
                            className="input"
                            type="range"
                            min={10}
                            max={20}
                            defaultValue={fontSize}
                            onChange={(e) =>
                                onSave({
                                    fontSize: Number(e.target.value),
                                    wordWrap,
                                    autoCompile,
                                    compileDelayMs,
                                    theme,
                                })
                            }
                        />
                    </label>
                    <label style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                        <input
                            type="checkbox"
                            checked={wordWrap}
                            onChange={(e) =>
                                onSave({
                                    fontSize,
                                    wordWrap: e.target.checked,
                                    autoCompile,
                                    compileDelayMs,
                                    theme,
                                })
                            }
                        />
                        Word Wrap
                    </label>
                    <label style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                        <input
                            type="checkbox"
                            checked={autoCompile}
                            onChange={(e) =>
                                onSave({
                                    fontSize,
                                    wordWrap,
                                    autoCompile: e.target.checked,
                                    compileDelayMs,
                                    theme,
                                })
                            }
                        />
                        Auto Compile
                    </label>
                    <label>
                        Compile Delay ({compileDelayMs} ms)
                        <input
                            className="input"
                            type="range"
                            min={500}
                            max={3000}
                            step={100}
                            defaultValue={compileDelayMs}
                            onChange={(e) =>
                                onSave({
                                    fontSize,
                                    wordWrap,
                                    autoCompile,
                                    compileDelayMs: Number(e.target.value),
                                    theme,
                                })
                            }
                        />
                    </label>
                </div>
                <div style={{ marginTop: "1rem", display: "flex", justifyContent: "flex-end" }}>
                    <button className="btn btn-secondary" onClick={onClose}>
                        Close
                    </button>
                </div>
            </div>
        </div>
    );
}

