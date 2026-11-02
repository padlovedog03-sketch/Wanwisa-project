import { describe, it, expect } from 'vitest';
import { isValidHttpUrl, calculateFieldsProgress } from '../../src/utils/validation';

describe('isValidHttpUrl validation utility', () => {
  it('accepts valid https URL', () => {
    expect(isValidHttpUrl('https://drive.google.com/file/d/123/view')).toBe(true);
  });

  it('accepts valid http URL', () => {
    expect(isValidHttpUrl('http://example.com/document.pdf')).toBe(true);
  });

  it('rejects javascript: pseudo-protocol to prevent XSS', () => {
    expect(isValidHttpUrl('javascript:alert(1)')).toBe(false);
  });

  it('rejects data: URI', () => {
    expect(isValidHttpUrl('data:text/html,<script>alert(1)</script>')).toBe(false);
  });

  it('rejects empty string or whitespace', () => {
    expect(isValidHttpUrl('')).toBe(false);
    expect(isValidHttpUrl('   ')).toBe(false);
  });

  it('rejects invalid malformed URLs', () => {
    expect(isValidHttpUrl('not a url')).toBe(false);
  });
});

describe('calculateFieldsProgress utility', () => {
  it('returns 0 for empty object', () => {
    expect(calculateFieldsProgress({})).toBe(0);
  });

  it('returns 100 when all fields are populated', () => {
    const fields = { name: 'Teacher', school: 'School A', hours: 40 };
    expect(calculateFieldsProgress(fields)).toBe(100);
  });

  it('calculates partial completion accurately', () => {
    const fields = { name: 'Teacher', school: '', hours: 0, major: 'Math' };
    // 2 filled out of 4 = 50%
    expect(calculateFieldsProgress(fields)).toBe(50);
  });
});
