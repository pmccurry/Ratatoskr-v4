import { describe, expect, test } from 'vitest';
import {
  formatPnl,
  formatPercent,
  formatCurrency,
  formatNumber,
  formatPrice,
  formatBasisPoints,
  formatDateTime,
  formatTimeAgo,
  formatDecimal,
} from '@/lib/formatters';

// ---------------------------------------------------------------------------
// toNumber (tested indirectly through public functions)
// ---------------------------------------------------------------------------

describe('toNumber (indirect)', () => {
  test('null returns em dash via formatCurrency', () => {
    expect(formatCurrency(null)).toBe('—');
  });
  test('undefined returns em dash', () => {
    expect(formatCurrency(undefined)).toBe('—');
  });
  test('NaN returns em dash', () => {
    expect(formatCurrency(NaN)).toBe('—');
  });
  test('string number is parsed', () => {
    expect(formatCurrency('100')).toContain('100');
  });
  test('non-numeric string returns em dash', () => {
    expect(formatCurrency('abc')).toBe('—');
  });
  test('empty string returns em dash', () => {
    expect(formatCurrency('')).toBe('—');
  });
  test('object returns em dash', () => {
    expect(formatCurrency({})).toBe('—');
  });
  test('boolean returns em dash', () => {
    expect(formatCurrency(true)).toBe('—');
  });
});

// ---------------------------------------------------------------------------
// formatPnl
// ---------------------------------------------------------------------------

describe('formatPnl', () => {
  test('positive number has + sign and $', () => {
    expect(formatPnl(50)).toBe('+$50.00');
  });
  test('negative number has - sign and $', () => {
    expect(formatPnl(-50)).toBe('-$50.00');
  });
  test('zero shows +$0.00', () => {
    expect(formatPnl(0)).toBe('+$0.00');
  });
  test('large number with commas', () => {
    expect(formatPnl(1234567)).toContain('1,234,567');
  });
  test('small decimal', () => {
    expect(formatPnl(0.01)).toBe('+$0.01');
  });
  test('null returns em dash', () => {
    expect(formatPnl(null)).toBe('—');
  });
  test('undefined returns em dash', () => {
    expect(formatPnl(undefined)).toBe('—');
  });
  test('NaN returns em dash', () => {
    expect(formatPnl(NaN)).toBe('—');
  });
  test('string number is parsed', () => {
    expect(formatPnl('100')).toBe('+$100.00');
  });
  test('negative string number', () => {
    expect(formatPnl('-25.5')).toBe('-$25.50');
  });
});

// ---------------------------------------------------------------------------
// formatPercent
// ---------------------------------------------------------------------------

describe('formatPercent', () => {
  test('positive has + sign and %', () => {
    expect(formatPercent(12.5)).toBe('+12.50%');
  });
  test('negative has - sign and %', () => {
    expect(formatPercent(-12.5)).toBe('-12.50%');
  });
  test('zero shows +0.00%', () => {
    expect(formatPercent(0)).toBe('+0.00%');
  });
  test('null returns em dash', () => {
    expect(formatPercent(null)).toBe('—');
  });
  test('string number parsed', () => {
    expect(formatPercent('5.5')).toBe('+5.50%');
  });
  test('custom decimals', () => {
    expect(formatPercent(12.345, 1)).toBe('+12.3%');
  });
  test('NaN returns em dash', () => {
    expect(formatPercent(NaN)).toBe('—');
  });
});

// ---------------------------------------------------------------------------
// formatCurrency
// ---------------------------------------------------------------------------

describe('formatCurrency', () => {
  test('positive number with $', () => {
    expect(formatCurrency(1000)).toBe('$1,000.00');
  });
  test('zero', () => {
    expect(formatCurrency(0)).toBe('$0.00');
  });
  test('null returns em dash', () => {
    expect(formatCurrency(null)).toBe('—');
  });
  test('undefined returns em dash', () => {
    expect(formatCurrency(undefined)).toBe('—');
  });
  test('string number parsed', () => {
    expect(formatCurrency('50')).toBe('$50.00');
  });
});

// ---------------------------------------------------------------------------
// formatNumber
// ---------------------------------------------------------------------------

describe('formatNumber', () => {
  test('formats with locale separators', () => {
    expect(formatNumber(1000000)).toBe('1,000,000');
  });
  test('null returns em dash', () => {
    expect(formatNumber(null)).toBe('—');
  });
  test('undefined returns em dash', () => {
    expect(formatNumber(undefined)).toBe('—');
  });
  test('string number parsed', () => {
    expect(formatNumber('5000')).toBe('5,000');
  });
  test('NaN returns em dash', () => {
    expect(formatNumber(NaN)).toBe('—');
  });
});

// ---------------------------------------------------------------------------
// formatPrice
// ---------------------------------------------------------------------------

describe('formatPrice', () => {
  test('equities format with $ and 2 decimals', () => {
    expect(formatPrice(150.5)).toBe('$150.50');
  });
  test('forex format with 5 decimals', () => {
    expect(formatPrice(1.2345, 'forex')).toBe('1.23450');
  });
  test('null returns em dash', () => {
    expect(formatPrice(null)).toBe('—');
  });
  test('undefined returns em dash', () => {
    expect(formatPrice(undefined)).toBe('—');
  });
  test('string number parsed', () => {
    expect(formatPrice('100')).toBe('$100.00');
  });
});

// ---------------------------------------------------------------------------
// formatBasisPoints
// ---------------------------------------------------------------------------

describe('formatBasisPoints', () => {
  test('formats with bps suffix', () => {
    expect(formatBasisPoints(5)).toBe('5bps');
  });
  test('null returns em dash', () => {
    expect(formatBasisPoints(null)).toBe('—');
  });
  test('undefined returns em dash', () => {
    expect(formatBasisPoints(undefined)).toBe('—');
  });
  test('zero', () => {
    expect(formatBasisPoints(0)).toBe('0bps');
  });
  test('NaN returns em dash', () => {
    expect(formatBasisPoints(NaN)).toBe('—');
  });
});

// ---------------------------------------------------------------------------
// formatDateTime
// ---------------------------------------------------------------------------

describe('formatDateTime', () => {
  test('formats ISO string', () => {
    const result = formatDateTime('2024-06-15T14:30:00Z');
    expect(result).toContain('2024');
    expect(result).not.toBe('—');
  });
  test('null returns em dash', () => {
    expect(formatDateTime(null)).toBe('—');
  });
  test('undefined returns em dash', () => {
    expect(formatDateTime(undefined)).toBe('—');
  });
  test('invalid date string returns em dash', () => {
    expect(formatDateTime('not-a-date')).toBe('—');
  });
  test('non-string returns em dash', () => {
    expect(formatDateTime(12345)).toBe('—');
  });
});

// ---------------------------------------------------------------------------
// formatTimeAgo
// ---------------------------------------------------------------------------

describe('formatTimeAgo', () => {
  test('recent timestamp shows seconds', () => {
    const now = new Date().toISOString();
    const result = formatTimeAgo(now);
    expect(result).toMatch(/\ds ago/);
  });
  test('5 minutes ago', () => {
    const fiveMinAgo = new Date(Date.now() - 5 * 60 * 1000).toISOString();
    expect(formatTimeAgo(fiveMinAgo)).toBe('5m ago');
  });
  test('null returns em dash', () => {
    expect(formatTimeAgo(null)).toBe('—');
  });
  test('undefined returns em dash', () => {
    expect(formatTimeAgo(undefined)).toBe('—');
  });
  test('non-string returns em dash', () => {
    expect(formatTimeAgo(123)).toBe('—');
  });
});

// ---------------------------------------------------------------------------
// formatDecimal
// ---------------------------------------------------------------------------

describe('formatDecimal', () => {
  test('formats number with decimals', () => {
    expect(formatDecimal(12.3456, 2)).toBe('12.35');
  });
  test('formats string number', () => {
    expect(formatDecimal('5.5', 3)).toBe('5.500');
  });
  test('null returns em dash', () => {
    expect(formatDecimal(null, 2)).toBe('—');
  });
  test('undefined returns em dash', () => {
    expect(formatDecimal(undefined, 2)).toBe('—');
  });
  test('NaN string returns em dash', () => {
    expect(formatDecimal('abc', 2)).toBe('—');
  });
});
