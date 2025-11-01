import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';

const ThemeContext = createContext();

const SKINS = {
  aurora: {
    name: 'Aurora',
    description: 'Gradient nocturne vibrant',
    variables: {
      '--accent': '#5d8bff',
      '--accent-soft': 'rgba(93, 139, 255, 0.22)',
      '--glow-strong': 'rgba(123, 97, 255, 0.38)',
    },
  },
  cyberpunk: {
    name: 'Cyberpunk',
    description: 'Neons magenta et cyan',
    variables: {
      '--accent': '#ff71ff',
      '--accent-soft': 'rgba(255, 113, 255, 0.2)',
      '--glow-strong': 'rgba(255, 113, 255, 0.45)',
      '--bg-secondary': 'radial-gradient(160% 140% at 20% 10%, rgba(255, 113, 255, 0.18), transparent 60%), radial-gradient(140% 120% at 90% 10%, rgba(0, 255, 255, 0.18), transparent 55%), linear-gradient(180deg, #060012 0%, #05051d 85%)',
    },
  },
  solar: {
    name: 'Solar',
    description: 'Palette douce jaune et orange',
    variables: {
      '--accent': '#f59e0b',
      '--accent-soft': 'rgba(245, 158, 11, 0.18)',
      '--glow-strong': 'rgba(245, 158, 11, 0.35)',
      '--bg-secondary': 'radial-gradient(140% 140% at 30% 20%, rgba(254, 240, 138, 0.25), transparent 55%), radial-gradient(140% 120% at 90% 10%, rgba(252, 211, 77, 0.22), transparent 55%), linear-gradient(180deg, #fef9c3 0%, #fef3c7 80%)',
    },
  },
  minimal: {
    name: 'Minimal',
    description: 'Design epure neutre',
    variables: {
      '--accent': '#2563eb',
      '--accent-soft': 'rgba(37, 99, 235, 0.16)',
      '--glow-strong': 'rgba(37, 99, 235, 0.25)',
      '--bg-secondary': 'linear-gradient(180deg, #f5f7fb 0%, #e9ecf5 80%)',
    },
  },
};

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(() => {
    if (typeof window === 'undefined') return 'dark';
    const stored = window.localStorage.getItem('dashboard-theme');
    if (stored) return stored;
    const prefersLight = window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches;
    return prefersLight ? 'light' : 'dark';
  });
  const [skin, setSkin] = useState(() => {
    if (typeof window === 'undefined') return 'aurora';
    return window.localStorage.getItem('dashboard-skin') || 'aurora';
  });

  useEffect(() => {
    if (typeof document === 'undefined') return;
    document.documentElement.setAttribute('data-theme', theme);
    document.body.setAttribute('data-theme', theme);
    window.localStorage.setItem('dashboard-theme', theme);
  }, [theme]);

  useEffect(() => {
    if (typeof document === 'undefined') return;
    const skinDef = SKINS[skin] || SKINS.aurora;
    Object.entries(skinDef.variables).forEach(([key, value]) => {
      document.documentElement.style.setProperty(key, value);
    });
    window.localStorage.setItem('dashboard-skin', skin);
  }, [skin]);

  const value = useMemo(() => ({
    theme,
    setTheme,
    toggleTheme: () => setTheme((prev) => (prev === 'dark' ? 'light' : 'dark')),
    skin,
    setSkin,
    skins: SKINS,
  }), [theme, skin]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider');
  return ctx;
}
