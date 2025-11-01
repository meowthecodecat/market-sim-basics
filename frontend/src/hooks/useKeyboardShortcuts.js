import { useEffect } from "react";
import { useUI } from "../context/UIContext.jsx";
import { useTheme } from "../context/ThemeContext.jsx";

export default function useKeyboardShortcuts() {
  const { dispatch } = useUI();
  const { toggleTheme } = useTheme();

  useEffect(() => {
    const handler = (event) => {
      const key = event.key.toLowerCase();
      if (key === 'o') {
        event.preventDefault();
        dispatch({ type: 'TOGGLE_SIDEBAR' });
      } else if (key === 't') {
        event.preventDefault();
        toggleTheme();
      } else if (key === 'f') {
        event.preventDefault();
        dispatch({ type: 'TOGGLE_FOCUS' });
      } else if (key === 'l') {
        event.preventDefault();
        dispatch({ type: 'TOGGLE_LARGE_TEXT' });
      } else if (key === 's') {
        event.preventDefault();
        dispatch({ type: 'TOGGLE_SOUND' });
      } else if (key === '?') {
        event.preventDefault();
        dispatch({ type: 'SHOW_SHORTCUTS' });
      } else if (key === 'escape') {
        dispatch({ type: 'HIDE_SHORTCUTS' });
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [dispatch, toggleTheme]);
}
