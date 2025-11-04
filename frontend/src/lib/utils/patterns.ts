/**
 * Pattern generator for geology layer textures
 * Provides distinct patterns for colorblind accessibility
 * Each pattern corresponds to a specific rock type in the data
 */

export type GeologyType =
  | 'unconsolidated-undifferentiated'
  | 'metamorphic-schist'
  | 'metamorphic-sedimentary-clastic'
  | 'metamorphic-undifferentiated'
  | 'metamorphic-volcanic'
  | 'melange'
  | 'igneous-intrusive'
  | 'water'
  | 'other';

/**
 * Generate a pattern as ImageData for MapLibre GL
 * Patterns are 64x64px for good quality at various zoom levels
 */
export function generatePattern(type: GeologyType, color: string): ImageData {
  const size = 64;
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d');

  if (!ctx) {
    throw new Error('Could not get canvas context');
  }

  // Set base color with transparency
  ctx.fillStyle = color;
  ctx.globalAlpha = 0.6;
  ctx.fillRect(0, 0, size, size);

  // Reset alpha for pattern lines
  ctx.globalAlpha = 1.0;
  ctx.strokeStyle = adjustColor(color, -30); // Darker version of base color
  ctx.lineWidth = 2;

  switch (type) {
    case 'unconsolidated-undifferentiated':
      // Horizontal lines
      for (let y = 0; y < size; y += 8) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(size, y);
        ctx.stroke();
      }
      break;

    case 'metamorphic-schist':
      // Diagonal lines (45°) - standard metamorphic pattern
      for (let i = -size; i < size * 2; i += 8) {
        ctx.beginPath();
        ctx.moveTo(i, 0);
        ctx.lineTo(i + size, size);
        ctx.stroke();
      }
      break;

    case 'metamorphic-sedimentary-clastic':
      // Dots - reflects sedimentary origin
      ctx.fillStyle = adjustColor(color, -30);
      for (let y = 4; y < size; y += 12) {
        for (let x = 4; x < size; x += 12) {
          ctx.beginPath();
          ctx.arc(x, y, 2, 0, Math.PI * 2);
          ctx.fill();
        }
      }
      break;

    case 'metamorphic-undifferentiated':
      // Lighter diagonal lines (wider spacing than schist)
      for (let i = -size; i < size * 2; i += 12) {
        ctx.beginPath();
        ctx.moveTo(i, 0);
        ctx.lineTo(i + size, size);
        ctx.stroke();
      }
      break;

    case 'metamorphic-volcanic':
      // Vertical lines - reflects volcanic origin
      for (let x = 0; x < size; x += 8) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, size);
        ctx.stroke();
      }
      break;

    case 'melange':
      // Sparse dots - reflects mixed/chaotic nature
      ctx.fillStyle = adjustColor(color, -30);
      for (let y = 8; y < size; y += 16) {
        for (let x = 8; x < size; x += 16) {
          ctx.beginPath();
          ctx.arc(x, y, 2, 0, Math.PI * 2);
          ctx.fill();
        }
      }
      break;

    case 'igneous-intrusive':
      // Crosshatch
      for (let i = -size; i < size * 2; i += 12) {
        ctx.beginPath();
        ctx.moveTo(i, 0);
        ctx.lineTo(i + size, size);
        ctx.stroke();

        ctx.beginPath();
        ctx.moveTo(i, size);
        ctx.lineTo(i + size, 0);
        ctx.stroke();
      }
      break;

    case 'water':
      // Waves/ripples
      ctx.beginPath();
      for (let y = 0; y < size; y += 12) {
        ctx.moveTo(0, y);
        for (let x = 0; x <= size; x += 4) {
          const wave = Math.sin((x / size) * Math.PI * 4) * 2;
          ctx.lineTo(x, y + wave);
        }
      }
      ctx.stroke();
      break;

    case 'other':
      // Very sparse dots - fallback
      ctx.fillStyle = adjustColor(color, -30);
      for (let y = 16; y < size; y += 24) {
        for (let x = 16; x < size; x += 24) {
          ctx.beginPath();
          ctx.arc(x, y, 2, 0, Math.PI * 2);
          ctx.fill();
        }
      }
      break;
  }

  return ctx.getImageData(0, 0, size, size);
}

/**
 * Adjust color brightness
 * amount: negative to darken, positive to lighten
 */
function adjustColor(color: string, amount: number): string {
  // Convert hex to RGB
  const hex = color.replace('#', '');
  const r = parseInt(hex.substring(0, 2), 16);
  const g = parseInt(hex.substring(2, 4), 16);
  const b = parseInt(hex.substring(4, 6), 16);

  // Adjust and clamp
  const newR = Math.max(0, Math.min(255, r + amount));
  const newG = Math.max(0, Math.min(255, g + amount));
  const newB = Math.max(0, Math.min(255, b + amount));

  // Convert back to hex
  return `#${newR.toString(16).padStart(2, '0')}${newG.toString(16).padStart(2, '0')}${newB.toString(16).padStart(2, '0')}`;
}

/**
 * Get all geology patterns with their colors
 */
export const geologyPatterns: Record<GeologyType, string> = {
  'unconsolidated-undifferentiated': '#d4d4d8',
  'metamorphic-schist': '#9333ea',
  'metamorphic-sedimentary-clastic': '#a855f7',
  'metamorphic-undifferentiated': '#8b5cf6',
  'metamorphic-volcanic': '#c084fc',
  'melange': '#7c3aed',
  'igneous-intrusive': '#f59e0b',
  'water': '#3b82f6',
  'other': '#9ca3af'
};

/**
 * Outfall determination types for inadequate outfalls layer
 * Provides colorblind-accessible patterns for stormwater problem areas
 */
export type OutfallDeterminationType =
  | 'erosion'
  | 'vertical-erosion'
  | 'left-bank-unstable'
  | 'right-bank-unstable'
  | 'both-banks-unstable'
  | 'habitat-score';

/**
 * Generate an outfall pattern as ImageData for MapLibre GL
 * Uses Okabe-Ito colorblind-safe palette
 */
export function generateOutfallPattern(type: OutfallDeterminationType, color: string): ImageData {
  const size = 64;
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d');

  if (!ctx) {
    throw new Error('Could not get canvas context');
  }

  // Set base color with transparency
  ctx.fillStyle = color;
  ctx.globalAlpha = 0.7;
  ctx.fillRect(0, 0, size, size);

  // Reset alpha for pattern lines
  ctx.globalAlpha = 1.0;
  ctx.strokeStyle = adjustColor(color, -20); // Softer contrast for less visual weight

  switch (type) {
    case 'erosion':
      // Crosshatch - widest spacing
      ctx.lineWidth = 2;
      for (let i = -size; i < size * 2; i += 16) {
        ctx.beginPath();
        ctx.moveTo(i, 0);
        ctx.lineTo(i + size, size);
        ctx.stroke();

        ctx.beginPath();
        ctx.moveTo(i, size);
        ctx.lineTo(i + size, 0);
        ctx.stroke();
      }
      break;

    case 'vertical-erosion':
      // Diagonal NW-SE - thinner line for smoother diagonal
      ctx.lineWidth = 1.5;
      for (let i = -size; i < size * 2; i += 16) {
        ctx.beginPath();
        ctx.moveTo(i, 0);
        ctx.lineTo(i + size, size);
        ctx.stroke();
      }
      break;

    case 'left-bank-unstable':
      // Diagonal NE-SW - thinner line for smoother diagonal
      ctx.lineWidth = 1.5;
      for (let i = -size; i < size * 2; i += 16) {
        ctx.beginPath();
        ctx.moveTo(i, size);
        ctx.lineTo(i + size, 0);
        ctx.stroke();
      }
      break;

    case 'right-bank-unstable':
      // Vertical lines
      ctx.lineWidth = 2;
      for (let x = 0; x < size; x += 16) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, size);
        ctx.stroke();
      }
      break;

    case 'both-banks-unstable':
      // Horizontal lines
      ctx.lineWidth = 2;
      for (let y = 0; y < size; y += 16) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(size, y);
        ctx.stroke();
      }
      break;

    case 'habitat-score':
      // Sparse dots - much wider spacing
      ctx.fillStyle = adjustColor(color, -20);
      for (let y = 8; y < size; y += 16) {
        for (let x = 8; x < size; x += 16) {
          ctx.beginPath();
          ctx.arc(x, y, 2, 0, Math.PI * 2);
          ctx.fill();
        }
      }
      break;
  }

  return ctx.getImageData(0, 0, size, size);
}

/**
 * Outfall patterns with Okabe-Ito colorblind-safe colors
 */
export const outfallPatterns: Record<OutfallDeterminationType, string> = {
  'erosion': '#E69F00',                    // Orange
  'vertical-erosion': '#D55E00',           // Vermillion
  'left-bank-unstable': '#56B4E9',         // Sky Blue
  'right-bank-unstable': '#0072B2',        // Blue
  'both-banks-unstable': '#009E73',        // Bluish Green
  'habitat-score': '#F0E442'               // Yellow
};

/**
 * Generate a pattern as data URL for CSS backgrounds (for legend)
 * Returns a smaller 24x24px pattern optimized for legend display
 */
export function generatePatternDataURL(type: GeologyType, color: string): string {
  const size = 24;
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d');

  if (!ctx) {
    return '';
  }

  // Set base color
  ctx.fillStyle = color;
  ctx.fillRect(0, 0, size, size);

  // Draw pattern
  ctx.strokeStyle = adjustColor(color, -40);
  ctx.lineWidth = 1.5;

  switch (type) {
    case 'unconsolidated-undifferentiated':
      for (let y = 0; y < size; y += 4) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(size, y);
        ctx.stroke();
      }
      break;

    case 'metamorphic-schist':
      for (let i = -size; i < size * 2; i += 4) {
        ctx.beginPath();
        ctx.moveTo(i, 0);
        ctx.lineTo(i + size, size);
        ctx.stroke();
      }
      break;

    case 'metamorphic-sedimentary-clastic':
      ctx.fillStyle = adjustColor(color, -40);
      for (let y = 3; y < size; y += 6) {
        for (let x = 3; x < size; x += 6) {
          ctx.beginPath();
          ctx.arc(x, y, 1.5, 0, Math.PI * 2);
          ctx.fill();
        }
      }
      break;

    case 'metamorphic-undifferentiated':
      for (let i = -size; i < size * 2; i += 6) {
        ctx.beginPath();
        ctx.moveTo(i, 0);
        ctx.lineTo(i + size, size);
        ctx.stroke();
      }
      break;

    case 'metamorphic-volcanic':
      for (let x = 0; x < size; x += 4) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, size);
        ctx.stroke();
      }
      break;

    case 'melange':
      ctx.fillStyle = adjustColor(color, -40);
      for (let y = 4; y < size; y += 8) {
        for (let x = 4; x < size; x += 8) {
          ctx.beginPath();
          ctx.arc(x, y, 1.5, 0, Math.PI * 2);
          ctx.fill();
        }
      }
      break;

    case 'igneous-intrusive':
      for (let i = -size; i < size * 2; i += 6) {
        ctx.beginPath();
        ctx.moveTo(i, 0);
        ctx.lineTo(i + size, size);
        ctx.stroke();

        ctx.beginPath();
        ctx.moveTo(i, size);
        ctx.lineTo(i + size, 0);
        ctx.stroke();
      }
      break;

    case 'water':
      ctx.beginPath();
      for (let y = 0; y < size; y += 6) {
        ctx.moveTo(0, y);
        for (let x = 0; x <= size; x += 2) {
          const wave = Math.sin((x / size) * Math.PI * 4) * 1;
          ctx.lineTo(x, y + wave);
        }
      }
      ctx.stroke();
      break;

    case 'other':
      ctx.fillStyle = adjustColor(color, -40);
      for (let y = 6; y < size; y += 12) {
        for (let x = 6; x < size; x += 12) {
          ctx.beginPath();
          ctx.arc(x, y, 1.5, 0, Math.PI * 2);
          ctx.fill();
        }
      }
      break;
  }

  return canvas.toDataURL();
}
