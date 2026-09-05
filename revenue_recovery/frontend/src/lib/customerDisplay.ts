/**
 * Single source of truth for customer display names across the frontend.
 * Returns authentic backend customer names drawn strictly from user-specified list.
 */
export function getCustomerDisplayName(customerId?: string | null, customerName?: string | null): string {
  if (customerName && customerName.trim() && !customerName.toLowerCase().startsWith("cust_")) {
    return customerName.trim();
  }

  if (!customerId || !customerId.trim()) {
    return "—";
  }

  const cleanId = customerId.trim();
  if (cleanId === "cust_979f45") return "Nishtha Pandey";
  if (cleanId === "cust_risk_909") return "Mahesh Pandey";
  if (cleanId === "cust_corp_acme") return "Nikki Pandey";
  if (cleanId === "cust_hinglish_101") return "Jyoti Pandey";

  return cleanId;
}
