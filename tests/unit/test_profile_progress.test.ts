import { describe, it, expect } from 'vitest';
import { calculateFieldsProgress } from '../../src/utils/validation';

describe('Profile Progress Calculation (AC1)', () => {
  it('calculates profile completion correctly from complete teacher profile', () => {
    const profile = {
      reportTitle: 'รายงานฝึกสอน',
      studentName: 'สมใจ ครูไทย',
      studentId: '1234567890',
      major: 'การประถมศึกษา',
      institution: 'มหาวิทยาลัยราชภัฏ',
      schoolName: 'โรงเรียนอนุบาล',
      semester: '1/2569',
      practicumPeriod: 'มิ.ย. - ก.ย.',
      teachingHours: 48,
    };
    expect(calculateFieldsProgress(profile)).toBe(100);
  });

  it('calculates partial progress when fields are empty', () => {
    const profile = {
      reportTitle: 'รายงานฝึกสอน',
      studentName: 'สมใจ ครูไทย',
      studentId: '',
      major: '',
      institution: '',
      schoolName: '',
      semester: '',
      practicumPeriod: '',
      teachingHours: 0,
    };
    // 2 out of 9 fields = 22%
    expect(calculateFieldsProgress(profile)).toBe(22);
  });
});
