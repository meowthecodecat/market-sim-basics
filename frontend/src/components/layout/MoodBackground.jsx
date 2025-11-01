import React, { useEffect, useRef } from "react";
import { useData } from "../../context/DataContext.jsx";

export default function MoodBackground() {
  const canvasRef = useRef(null);
  const animationRef = useRef(null);
  const { mood, moodIntensity } = useData();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let width, height;

    const resize = () => {
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener('resize', resize);

    const hueBase = mood === 'negative' ? 350 : 210;

    const draw = (t) => {
      const intensity = moodIntensity ?? 0;
      const gradient = ctx.createRadialGradient(
        width * 0.3,
        height * 0.3,
        0,
        width * 0.3,
        height * 0.3,
        Math.max(width, height)
      );
      const hueShift = Math.sin(t * 0.0002) * 20 * (intensity + 0.2);
      const hue = (hueBase + hueShift + 360) % 360;
      gradient.addColorStop(0, `hsla(${hue}, 88%, ${mood === 'negative' ? 45 : 55}%, ${0.25 + intensity / 2})`);
      gradient.addColorStop(1, 'rgba(5, 8, 20, 0.3)');

      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, width, height);

      animationRef.current = requestAnimationFrame(draw);
    };

    animationRef.current = requestAnimationFrame(draw);
    return () => {
      cancelAnimationFrame(animationRef.current);
      window.removeEventListener('resize', resize);
    };
  }, [mood, moodIntensity]);

  return <canvas ref={canvasRef} className="mood-background" aria-hidden="true" />;
}
