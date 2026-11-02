import { describe, it, expect } from 'vitest';
import { MAX_IMAGE_SIZE_BYTES, MAX_DIMENSION_PX } from '../../src/utils/compression';

describe('Image Compression Constants & Boundary Checks (AC5)', () => {
  it('enforces maximum image size boundary of 200KB', () => {
    expect(MAX_IMAGE_SIZE_BYTES).toBe(200 * 1024);
  });

  it('enforces maximum dimension of 600px', () => {
    expect(MAX_DIMENSION_PX).toBe(600);
  });
});
