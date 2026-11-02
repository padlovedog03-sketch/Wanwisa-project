import { useState, useEffect, useCallback } from 'react';
import { PortfolioState } from '../types/portfolio';
import { loadLocalPortfolio, saveLocalPortfolio } from '../services/storage';

export function usePortfolioState() {
  const [state, setState] = useState<PortfolioState>(loadLocalPortfolio);
  const [isDirty, setIsDirty] = useState<boolean>(false);
  const [lastSaved, setLastSaved] = useState<string>('');

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

  const saveAll = useCallback(() => {
    const success = saveLocalPortfolio(state);
    if (success) {
      setIsDirty(false);
      setLastSaved(new Date().toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit' }));
      return true;
    }
    return false;
  }, [state]);

  const resetToSaved = useCallback(() => {
    setState(loadLocalPortfolio());
    setIsDirty(false);
  }, []);

  return {
    state,
    updateState,
    isDirty,
    lastSaved,
    saveAll,
    resetToSaved,
  };
}
