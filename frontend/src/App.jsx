import React from 'react';
import { ThemeProvider } from './context/ThemeContext.jsx';
import { UIProvider, useUI } from './context/UIContext.jsx';
import { DataProvider } from './context/DataContext.jsx';
import MoodBackground from './components/layout/MoodBackground.jsx';
import HeaderSection from './components/layout/HeaderSection.jsx';
import MetricGrid from './components/metrics/MetricGrid.jsx';
import ChartsSection from './components/charts/ChartsSection.jsx';
import MicrostructureSection from './components/panels/MicrostructureSection.jsx';
import TablesSection from './components/tables/TablesSection.jsx';
import StoryCluster from './components/stories/StoryCluster.jsx';
import StrategyLab from './components/panels/StrategyLab.jsx';
import ThemeGallery from './components/panels/ThemeGallery.jsx';
import PersonalizationBar from './components/panels/PersonalizationBar.jsx';
import ShortcutsOverlay from './components/widgets/ShortcutsOverlay.jsx';
import OrderBookSidebar from './components/panels/OrderBookSidebar.jsx';
import useKeyboardShortcuts from './hooks/useKeyboardShortcuts.js';
import useGestures from './hooks/useGestures.js';
import './styles/app-shell.css';

function AppShell() {
  const { focusMode, showShortcuts, isSidebarOpen } = useUI();

  useKeyboardShortcuts();
  useGestures();

  return (
    <div className={`app-shell ${focusMode ? 'focus-mode' : ''}`}>
      <MoodBackground />
      <HeaderSection />
      <PersonalizationBar />
      <MetricGrid />
      <StoryCluster />
      <ChartsSection />
      <MicrostructureSection />
      <StrategyLab />
      <ThemeGallery />
      <TablesSection />
      <footer className="footer">Powered by Kraken live data. Real-time simulation for inspired traders.</footer>
      {showShortcuts && <ShortcutsOverlay />}
      <OrderBookSidebar open={isSidebarOpen} />
    </div>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <UIProvider>
        <DataProvider>
          <AppShell />
        </DataProvider>
      </UIProvider>
    </ThemeProvider>
  );
}
