import { useEffect } from "react";
import { useUI } from "../context/UIContext.jsx";

export default function useGestures() {
  const { dispatch } = useUI();
  useEffect(() => {
    let startX = null;
    const onTouchStart = (e) => {
      startX = e.touches[0].clientX;
    };
    const onTouchEnd = (e) => {
      if (startX == null) return;
      const endX = e.changedTouches[0].clientX;
      const delta = endX - startX;
      if (delta > 120) {
        dispatch({ type: 'TOGGLE_SIDEBAR', value: true });
      } else if (delta < -120) {
        dispatch({ type: 'TOGGLE_SIDEBAR', value: false });
      }
      startX = null;
    };
    window.addEventListener('touchstart', onTouchStart);
    window.addEventListener('touchend', onTouchEnd);
    return () => {
      window.removeEventListener('touchstart', onTouchStart);
      window.removeEventListener('touchend', onTouchEnd);
    };
  }, [dispatch]);
}
