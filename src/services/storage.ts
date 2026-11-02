import { PortfolioState } from '../types/portfolio';
import { INITIAL_PORTFOLIO_STATE } from './initialData';

export { INITIAL_PORTFOLIO_STATE };

const LOCAL_STORAGE_KEY = "teaching-practice-report-data-v5";

export function loadLocalPortfolio(): PortfolioState {
  try {
    const raw = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (!raw) return INITIAL_PORTFOLIO_STATE;
    const parsed = JSON.parse(raw);
    return { ...INITIAL_PORTFOLIO_STATE, ...parsed };
  } catch {
    return INITIAL_PORTFOLIO_STATE;
  }
}

export function saveLocalPortfolio(state: PortfolioState): boolean {
  try {
    localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(state));
    return true;
  } catch (error) {
    console.error("Failed to save to localStorage:", error);
    return false;
  }
}

/**
 * Syncs the portfolio state to PostgreSQL via Vercel Serverless Function (/api/portfolio)
 */
export async function syncWithPostgres(state: PortfolioState): Promise<boolean> {
  try {
    const res = await fetch('/api/portfolio', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(state),
    });
    return res.ok;
  } catch (err) {
    console.warn("Postgres sync skipped or failed (offline / local):", err);
    return false;
  }
}

/**
 * Fetches the latest portfolio state from PostgreSQL via Vercel Serverless Function
 */
export async function fetchFromPostgres(): Promise<PortfolioState | null> {
  try {
    const res = await fetch('/api/portfolio');
    if (!res.ok) return null;
    const result = await res.json();
    if (result.found && result.data) {
      return { ...INITIAL_PORTFOLIO_STATE, ...result.data };
    }
    return null;
  } catch (err) {
    console.warn("Could not fetch from Postgres:", err);
    return null;
  }
}

/**
 * Parses and maps Firebase dump JSON into valid PortfolioState
 */
export function importPortfolioFromJson(rawJson: string): PortfolioState {
  const parsed = JSON.parse(rawJson);
  let target = parsed;
  if (parsed.teachingPracticeReport && parsed.teachingPracticeReport.data) {
    target = parsed.teachingPracticeReport.data;
    if (parsed.teaching_internship && parsed.teaching_internship.research) {
      target.research = { ...target.research, ...parsed.teaching_internship.research };
    }
  } else if (parsed.data) {
    target = parsed.data;
  }

  return {
    ...INITIAL_PORTFOLIO_STATE,
    ...target,
    profile: { ...INITIAL_PORTFOLIO_STATE.profile, ...(target.profile || {}) },
    school: { ...INITIAL_PORTFOLIO_STATE.school, ...(target.school || {}) },
    settings: { ...INITIAL_PORTFOLIO_STATE.settings, ...(target.settings || {}) },
  };
}
