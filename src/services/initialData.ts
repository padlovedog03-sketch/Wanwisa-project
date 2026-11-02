import { PortfolioState } from '../types/portfolio';
import convertedData from '../../converted-portfolio-data.json';

export const INITIAL_PORTFOLIO_STATE: PortfolioState = convertedData as unknown as PortfolioState;

