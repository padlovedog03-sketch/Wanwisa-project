import { useState, useEffect, useCallback } from 'react';
import { PortfolioState } from '../types/portfolio';
import {
  loadLocalPortfolio,
  saveLocalPortfolio,
  syncWithPostgres,
  fetchFromPostgres,
  importPortfolioFromJson,
} from '../services/storage';

export function usePortfolioState() {
  const [state, setState] = useState<PortfolioState>(loadLocalPortfolio);
  const [isDirty, setIsDirty] = useState<boolean>(false);
  const [lastSaved, setLastSaved] = useState<string>('');

  // Initial fetch from PostgreSQL if running on Vercel
  useEffect(() => {
    fetchFromPostgres().then((remoteData) => {
      if (remoteData) {
        setState(remoteData);
        saveLocalPortfolio(remoteData);
      }
    });
  }, []);

  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (isDirty) {
        e.preventDefault();
        e.returnValue = '';
      }
    };
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [isDirty]);

  const updateState = useCallback(<K extends keyof PortfolioState>(key: K, value: PortfolioState[K]) => {
    setState((prev) => ({
      ...prev,
      [key]: value,
    }));
    setIsDirty(true);
  }, []);

  const saveAll = useCallback(async (overrideState?: PortfolioState) => {
    const dataToSave = overrideState || state;
    const localOk = saveLocalPortfolio(dataToSave);
    if (localOk) {
      if (overrideState) {
        setState(overrideState);
      }
      setIsDirty(false);
      setLastSaved(new Date().toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit' }));
      // Asynchronously sync with PostgreSQL
      syncWithPostgres(dataToSave);
      return true;
    }
    return false;
  }, [state]);

  const resetToSaved = useCallback(() => {
    setState(loadLocalPortfolio());
    setIsDirty(false);
  }, []);

  const importFromDump = useCallback((jsonString: string) => {
    try {
      const imported = importPortfolioFromJson(jsonString);
      setState(imported);
      saveLocalPortfolio(imported);
      syncWithPostgres(imported);
      setIsDirty(false);
      setLastSaved(new Date().toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit' }));
      return true;
    } catch (err) {
      console.error("Failed to parse and import JSON dump:", err);
      return false;
    }
  }, []);

  return {
    state,
    updateState,
    isDirty,
    lastSaved,
    saveAll,
    resetToSaved,
    importFromDump,
  };
}
