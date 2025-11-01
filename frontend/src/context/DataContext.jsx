import React, { createContext, useContext, useMemo, useState } from 'react';
import { useTheme } from './ThemeContext.jsx';
import { useUI } from './UIContext.jsx';
import useDashboardData from '../hooks/useDashboardData.js';

const DataContext = createContext();

export function DataProvider({ children }) {
  const [orderbookDepth, setOrderbookDepth] = useState(25);
  const dashboard = useDashboardData(orderbookDepth);
  const { state, dispatch } = useUI();
  const { theme } = useTheme();

  const value = useMemo(() => ({
    ...dashboard,
    orderbookDepth,
    setOrderbookDepth,
    theme,
    uiState: state,
    uiDispatch: dispatch,
  }), [dashboard, orderbookDepth, theme, state, dispatch]);

  return <DataContext.Provider value={value}>{children}</DataContext.Provider>;
}

export function useData() {
  const ctx = useContext(DataContext);
  if (!ctx) throw new Error('useData must be used within DataProvider');
  return ctx;
}
