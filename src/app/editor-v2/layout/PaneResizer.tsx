"use client";

import { useCallback, useRef } from "react";

type PaneResizerProps = {
    axis: "vertical" | "horizontal";
    onDelta: (delta: number) => void;
};

export default function PaneResizer({ axis, onDelta }: PaneResizerProps) {
    const startRef = useRef<number | null>(null);

    const onPointerDown = useCallback(
        (e: React.PointerEvent<HTMLDivElement>) => {
            e.preventDefault();
            startRef.current = axis === "vertical" ? e.clientX : e.clientY;
            const handleMove = (moveEvent: PointerEvent) => {
                if (startRef.current == null) return;
                const current = axis === "vertical" ? moveEvent.clientX : moveEvent.clientY;
                const delta = current - startRef.current;
                if (Math.abs(delta) < 2) return;
                onDelta(delta);
                startRef.current = current;
            };
            const handleUp = () => {
                startRef.current = null;
                window.removeEventListener("pointermove", handleMove);
                window.removeEventListener("pointerup", handleUp);
            };
            window.addEventListener("pointermove", handleMove);
            window.addEventListener("pointerup", handleUp);
        },
        [axis, onDelta]
    );

    return (
        <div
            onPointerDown={onPointerDown}
            style={{
                cursor: axis === "vertical" ? "col-resize" : "row-resize",
                background: "transparent",
                userSelect: "none",
                touchAction: "none",
            }}
            aria-hidden
        />
    );
}

