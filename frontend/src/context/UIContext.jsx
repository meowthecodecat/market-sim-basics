import React, { createContext, useContext, useEffect, useMemo, useReducer } from 'react';

const UIContext = createContext();

const initialState = {
  focusMode: false,
  soundEnabled: false,
  showShortcuts: false,
  isSidebarOpen: false,
  largeText: false,
  textOnly: false,
};

function reducer(state, action) {
  switch (action.type) {
    case 'TOGGLE_FOCUS':
      return { ...state, focusMode: !state.focusMode };
    case 'TOGGLE_SOUND':
      return { ...state, soundEnabled: !state.soundEnabled };
    case 'SHOW_SHORTCUTS':
      return { ...state, showShortcuts: true };
    case 'HIDE_SHORTCUTS':
      return { ...state, showShortcuts: false };
    case 'TOGGLE_SIDEBAR':
      return { ...state, isSidebarOpen: action.value ?? !state.isSidebarOpen };
    case 'TOGGLE_LARGE_TEXT':
      return { ...state, largeText: !state.largeText };
    case 'TOGGLE_TEXT_ONLY':
      return { ...state, textOnly: !state.textOnly };
    default:
      return state;
  }
}

export function UIProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, initialState, (init) => {
    if (typeof window === 'undefined') return init;
    const stored = window.localStorage.getItem('ui-preferences');
    if (stored) {
      try { return { ...init, ...JSON.parse(stored) }; }
      catch { return init; }
    }
    return init;
  });

  useEffect(() => {
    if (typeof document === 'undefined') return;
    document.body.classList.toggle('focus-mode', state.focusMode);
    document.body.classList.toggle('large-text-mode', state.largeText);
    document.body.classList.toggle('text-only-mode', state.textOnly);
    window.localStorage.setItem('ui-preferences', JSON.stringify({
      focusMode: state.focusMode,
      soundEnabled: state.soundEnabled,
      largeText: state.largeText,
      textOnly: state.textOnly,
    }));
  }, [state.focusMode, state.largeText, state.textOnly, state.soundEnabled]);

  const value = useMemo(() => ({ state, dispatch,
    focusMode: state.focusMode,
    soundEnabled: state.soundEnabled,
    showShortcuts: state.showShortcuts,
    isSidebarOpen: state.isSidebarOpen,
    largeText: state.largeText,
    textOnly: state.textOnly,
  }), [state]);

  return <UIContext.Provider value={value}>{children}</UIContext.Provider>;
}

export function useUI() {
  const ctx = useContext(UIContext);
  if (!ctx) throw new Error('useUI must be used within UIProvider');
  return ctx;
}
