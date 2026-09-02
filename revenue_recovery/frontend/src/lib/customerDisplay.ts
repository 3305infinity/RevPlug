/**
 * Single source of truth for customer display names across the frontend.
 * Never fabricates real company names from customer IDs.
 * Uses valid backend names when present, or formats neutral identifiers.
 */
export function getCustomerDisplayName(customerId?: string | null, customerName?: string | null): string {
  // If name is valid, non-empty, and NOT a raw error-code string (e.g. Customer_404, Customer_202, cust_xxx)
  if (customerName && customerName.trim()) {
    const trimmed = customerName.trim();
    const isRawCodePattern = /^(Customer|Acme Corporation|cust)_?\d*$/i.test(trimmed) || 
                             /_\d{3,}$/.test(trimmed) || 
                             /\s\d{3,}$/.test(trimmed) ||
                             trimmed.startsWith("cust_");
    if (!isRawCodePattern) {
      return trimmed;
    }
  }

  if (!customerId || !customerId.trim()) {
    return "—";
  }

  const cleanId = customerId.trim();

  // Extract numeric suffix if available (e.g. cust_demo_pivot_101 -> 101)
  const numMatch = cleanId.match(/(\d{3,})$/);
  if (numMatch) {
    return `Customer ${numMatch[1]}`;
  }

  // Deterministic hex hash label
  let hash = 0;
  for (let i = 0; i < cleanId.length; i++) {
    hash = (hash << 5) - hash + cleanId.charCodeAt(i);
    hash |= 0;
  }
  const hexHash = Math.abs(hash).toString(16).padStart(6, "0").slice(0, 6).toUpperCase();
  return `Customer ${hexHash}`;
}
