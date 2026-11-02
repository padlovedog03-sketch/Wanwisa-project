import { CompressedImage } from '../types/portfolio';

export const MAX_IMAGE_SIZE_BYTES = 200 * 1024; // 200KB limit
export const MAX_DIMENSION_PX = 600;

export interface CompressionResult {
  success: boolean;
  image?: CompressedImage;
  error?: string;
}

/**
 * Resizes an image file to max dimension and compresses to JPEG <= 200KB.
 */
export async function compressImageFile(file: File): Promise<CompressedImage> {
  if (!file || !file.type.startsWith('image/')) {
    throw new Error('INVALID_IMAGE_TYPE');
  }

  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error('FILE_READ_ERROR'));
    reader.onload = () => {
      const img = new Image();
      img.onerror = () => reject(new Error('IMAGE_DECODE_ERROR'));
      img.onload = () => {
        const maxSide = Math.max(img.width, img.height);
        const scale = Math.min(1, MAX_DIMENSION_PX / maxSide);
        const width = Math.max(1, Math.round(img.width * scale));
        const height = Math.max(1, Math.round(img.height * scale));

        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;

        const ctx = canvas.getContext('2d');
        if (!ctx) {
          return reject(new Error('CANVAS_CONTEXT_ERROR'));
        }

        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, width, height);
        ctx.drawImage(img, 0, 0, width, height);

        canvas.toBlob(
          (blob) => {
            if (!blob) return reject(new Error('CANVAS_BLOB_ERROR'));
            if (blob.size > MAX_IMAGE_SIZE_BYTES) {
              return reject(new Error('IMAGE_TOO_LARGE'));
            }

            const dataReader = new FileReader();
            dataReader.onloadend = () => {
              resolve({
                id: crypto.randomUUID(),
                fileName: file.name,
                compressedDataUrl: dataReader.result as string,
                compressedSize: blob.size,
              });
            };
            dataReader.readAsDataURL(blob);
          },
          'image/jpeg',
          0.6
        );
      };
      img.src = reader.result as string;
    };
    reader.readAsDataURL(file);
  });
}
