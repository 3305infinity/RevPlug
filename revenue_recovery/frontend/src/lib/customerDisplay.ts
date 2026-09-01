export const REALISTIC_ENTERPRISE_NAMES = [
  "Swiggy Enterprise Logistics",
  "Zomato Merchant Solutions",
  "Acme Global Pvt Ltd",
  "Flipkart Merchant Services",
  "Reliance Retail Tech",
  "Paytm Business Solutions",
  "InMobi Media Pvt Ltd",
  "Razorpay Enterprise Direct",
  "PhonePe Merchant Pay",
  "Freshworks SaaS Client",
];

const EXPLICIT_DEMO_NAME_MAP: Record<string, string> = {
  cust_demo_pivot_101: "Swiggy Enterprise Logistics",
  cust_demo_hard_202: "Zomato Merchant Solutions",
  cust_demo_dispute_303: "Acme Global Pvt Ltd",
  cust_demo_fraud_404: "Flipkart Merchant Services",
  cust_hinglish_505: "Reliance Retail Tech",
  cust_corp_acme: "Paytm Business Solutions",
  cust_ambig_707: "InMobi Media Pvt Ltd",
  cust_razor_101: "Swiggy Enterprise Logistics",
  cust_risk_909: "Flipkart Merchant Services",
  razorpay_customer: "Swiggy Enterprise Logistics",
};

/**
 * Single source of truth for customer display names across the frontend.
 * Never renders raw IDs with numeric error-code suffixes (like Customer_404 or Customer_202).
 */
export function getCustomerDisplayName(customerId?: string | null, customerName?: string | null): string {
  // If name is valid, non-empty, and NOT a raw error-code string (e.g. Customer_404, Customer_202, Acme Corporation 404, cust_xxx)
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

  if (!customerId) {
    return REALISTIC_ENTERPRISE_NAMES[0];
  }

  const cleanId = customerId.trim();

  // Check explicit mapping
  if (EXPLICIT_DEMO_NAME_MAP[cleanId]) {
    return EXPLICIT_DEMO_NAME_MAP[cleanId];
  }

  // Deterministic fallback based on character code sum
  let hash = 0;
  for (let i = 0; i < cleanId.length; i++) {
    hash = (hash << 5) - hash + cleanId.charCodeAt(i);
    hash |= 0;
  }
  const idx = Math.abs(hash) % REALISTIC_ENTERPRISE_NAMES.length;
  return REALISTIC_ENTERPRISE_NAMES[idx];
}
