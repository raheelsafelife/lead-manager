export function percentageOf(value, total) {
  const numericValue = Number(value);
  const numericTotal = Number(total);
  if (!Number.isFinite(numericValue) || !Number.isFinite(numericTotal) || numericTotal <= 0) return 0;
  return numericValue / numericTotal * 100;
}

export function formatPercentage(value, total) {
  return `${percentageOf(value, total).toFixed(1)}%`;
}
