import React, { useEffect, useRef } from "react";
import { useData } from "../../context/DataContext.jsx";
import { useUI } from "../../context/UIContext.jsx";

export default function AudioController() {
  const { signalEvent } = useData();
  const { state, dispatch } = useUI();
  const audioCtxRef = useRef(null);

  useEffect(() => {
    if (!signalEvent || !state.soundEnabled) return;
    const ctx = audioCtxRef.current || new (window.AudioContext || window.webkitAudioContext)();
    audioCtxRef.current = ctx;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    gain.gain.setValueAtTime(0.0001, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.1, ctx.currentTime + 0.01);
    gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.4);
    osc.type = 'sine';
    osc.frequency.value = signalEvent.signal > 0 ? 880 : 440;
    osc.connect(gain).connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.4);
  }, [signalEvent, state.soundEnabled]);

  return (
    <button
      className={`pill audio-toggle ${state.soundEnabled ? 'active' : ''}`}
      onClick={() => dispatch({ type: 'TOGGLE_SOUND' })}
      type="button"
    >
      {state.soundEnabled ? 'Sound on' : 'Sound off'}
    </button>
  );
}
