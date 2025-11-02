export const fmtCurrency = (value, opts = {}) => {
  if (value == null || Number.isNaN(Number(value))) return '--';
  const numericValue = Number(value);
  const baseOpts = {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
    ...opts,
  };
  if (baseOpts.minimumFractionDigits != null) {
    const minDigits = Number(baseOpts.minimumFractionDigits);
    const hasMax = baseOpts.maximumFractionDigits != null;
    const maxDigits = hasMax ? Number(baseOpts.maximumFractionDigits) : minDigits;
    baseOpts.minimumFractionDigits = minDigits;
    baseOpts.maximumFractionDigits = Math.max(maxDigits, minDigits);
  }
  return numericValue.toLocaleString('en-US', baseOpts);
};

export const fmtPercent = (value, opts = {}) => {
  if (value == null || Number.isNaN(Number(value))) return '--';
  const sign = value > 0 ? '+' : '';
  const decimals = opts.decimals ?? 2;
  return `${sign}${Number(value).toFixed(decimals)}%`;
};

export const fmtLatency = (value) => {
  if (value == null || Number.isNaN(Number(value))) return '--';
  return `${Math.round(Number(value))} ms`;
};

export const fmtDateTime = (iso) => {
  if (!iso) return '--';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '--';
  return d.toLocaleString('fr-FR', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    day: '2-digit',
    month: 'short',
  });
};

export const fmtBookPrice = (value) => {
  if (value == null || Number.isNaN(Number(value))) return '--';
  return Number(value).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

export const fmtBookQty = (value) => {
  if (value == null || Number.isNaN(Number(value))) return '--';
  return Number(value).toLocaleString('en-US', { minimumFractionDigits: 4, maximumFractionDigits: 6 });
};
