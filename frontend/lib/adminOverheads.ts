export type OverheadRow = {
  category: string;
  monthly: number[];
  annualTotal: number;
  comparisonTotal: number;
  extraValue?: number;
  kind?: "normal" | "subtotal" | "total";
};

export const MONTH_LABELS = ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9", "M10", "M11", "M12"];

export const OVERHEAD_ROWS: OverheadRow[] = [
  { category: "Travel & Motor", monthly: [507, 347, 327, 336, 654, 410, 427, 479, 693, 422, 415, 1265], annualTotal: 6282, comparisonTotal: 3488 },
  { category: "Motor Insurance", monthly: [239, 239, 239, 239, 239, 239, 239, 239, 239, 239, 239, 239], annualTotal: 2869, comparisonTotal: 1913 },
  { category: "Postage & Carriage", monthly: [3284, 1638, 1883, 577, 1001, 834, 695, 1088, 884, 710, 3505, 1639], annualTotal: 17739, comparisonTotal: 11001 },
  { category: "Software & Stationery", monthly: [334, 607, 644, 645, 804, 825, 690, 734, 431, 432, 504, 358], annualTotal: 7009, comparisonTotal: 5284 },
  { category: "Software Yearly Subscriptions", monthly: [95, 95, 95, 95, 95, 95, 95, 95, 95, 95, 95, 95], annualTotal: 1145, comparisonTotal: 763 },
  { category: "Telephone", monthly: [351, 451, 173, 133, 499, 143, 143, 492, 116, 131, 165, 133], annualTotal: 2931, comparisonTotal: 2385 },
  { category: "Book-keeping", monthly: [1080, 840, 1440, 1440, 1440, 1560, 1353, 1560, 1320, 1320, 1560, 960], annualTotal: 15873, comparisonTotal: 10713 },
  { category: "Audit & Accountancy", monthly: [108, 120, 108, 108, 108, 108, 108, 108, 108, 108, 108, 108], annualTotal: 1311, comparisonTotal: 878 },
  { category: "Legal & Professional", monthly: [156, 0, 0, 0, 0, 26, 29, 23, 403, 27, 0, 123], annualTotal: 787, comparisonTotal: 234 },
  { category: "Light & Heat", monthly: [1819, 1574, 2018, 2660, 2218, 2198, 2287, 1932, 2047, 2110, 1718, 1799], annualTotal: 24380, comparisonTotal: 16706 },
  { category: "Repairs & Renewals", monthly: [2315, 1803, 3097, 3237, 1612, 2105, 223, 1617, 1606, 673, 1286, 1084], annualTotal: 20657, comparisonTotal: 16009 },
  { category: "Yearly Maintenance Contracts", monthly: [119, 119, 119, 119, 119, 119, 119, 119, 119, 119, 119, 119], annualTotal: 1425, comparisonTotal: 950 },
  { category: "Property Repairs", monthly: [15, 0, 9, 453, 122, 0, 167, 0, 188, 50, 0, 0], annualTotal: 1004, comparisonTotal: 766, extraValue: 570.9 },
  { category: "Canteen & Cleaning", monthly: [59, 29, 208, 198, 82, 170, 87, 196, 182, 209, 109, 147], annualTotal: 1677, comparisonTotal: 1030 },
  { category: "Rent", monthly: [3550, 3550, 3550, 3550, 3550, 3550, 3550, 3550, 3550, 3550, 3550, 3550], annualTotal: 42600, comparisonTotal: 28400 },
  { category: "Mis Expenses", monthly: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1648], annualTotal: 1648, comparisonTotal: 0 },
  { category: "Subs / Donations", monthly: [6, 6, 6, 6, 6, 194, 6, 6, 6, 6, 6, 6], annualTotal: 256, comparisonTotal: 234 },
  { category: "Sub Total", monthly: [14038, 11418, 13917, 13796, 12549, 12577, 10219, 12240, 11988, 10200, 13380, 13272], annualTotal: 149594, comparisonTotal: 100754, kind: "subtotal" },
  { category: "Non-Prod wages", monthly: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], annualTotal: 0, comparisonTotal: 0 },
  { category: "NI", monthly: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], annualTotal: 0, comparisonTotal: 0 },
  { category: "Pension", monthly: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], annualTotal: 0, comparisonTotal: 0 },
  { category: "Sales wages", monthly: [2833, 2833, 2833, 2833, 2833, 2833, 2833, 2833, 2833, 2833, 2833, 2833], annualTotal: 34000, comparisonTotal: 22667 },
  { category: "NI (Sales)", monthly: [362, 362, 362, 286, 286, 362, 362, 362, 362, 362, 362, 362], annualTotal: 4197, comparisonTotal: 2747 },
  { category: "Pension (Sales)", monthly: [69, 69, 69, 69, 69, 69, 69, 69, 69, 69, 69, 69], annualTotal: 833, comparisonTotal: 555 },
  { category: "Insurance", monthly: [170, 170, 170, 170, 170, 170, 170, 170, 170, 170, 170, 170], annualTotal: 2039, comparisonTotal: 1359 },
  { category: "Rates", monthly: [1240, 1240, 1220, 1220, 1220, 1217, 1261, 1240, 1240, 1240, 1240, 1240], annualTotal: 14814, comparisonTotal: 9856 },
  { category: "Water", monthly: [96, 175, 97, 97, 108, 93, 88, 93, 88, 93, 93, 88], annualTotal: 1208, comparisonTotal: 846 },
  { category: "Bank Charges / Interest", monthly: [48, 1453, 804, 60, 1779, 54, 48, 1599, 135, 50, 1757, 54], annualTotal: 7842, comparisonTotal: 5845 },
  { category: "HP - Xerox Rental (1)", monthly: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], annualTotal: 0, comparisonTotal: 0 },
  { category: "Medical Insurance", monthly: [230, 230, 230, 231, 460, 230, 230, 230, 230, 230, 230, 230], annualTotal: 2991, comparisonTotal: 2071 },
  { category: "Depn Fixtures / Fittings", monthly: [126, 126, 185, 185, 22, 20, 98, 126, 126, 126, 126, 126], annualTotal: 1387, comparisonTotal: 885 },
  { category: "Depn Plant / Equipment", monthly: [2200, 2200, 2200, 2200, 2200, 2200, 2200, 500, 500, 500, 500, 500], annualTotal: 17900, comparisonTotal: 15900 },
  { category: "Depn Motor Vehicles", monthly: [840, 840, 840, 840, 840, 840, 840, 840, 840, 840, 840, 840], annualTotal: 10074, comparisonTotal: 6716 },
  { category: "HP - Xerox Rental (2)", monthly: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], annualTotal: 0, comparisonTotal: 0 },
  { category: "Motor Expenses - Bill", monthly: [441, 207, 390, 357, 454, 275, 345, 431, 371, 359, 283, 289], annualTotal: 4203, comparisonTotal: 2900 },
  { category: "Network / E-Mail", monthly: [50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50], annualTotal: 600, comparisonTotal: 400 },
  { category: "Entertainment", monthly: [88, 515, 291, 94, 629, 1078, 0, 125, 30, 172, 36, 140], annualTotal: 3197, comparisonTotal: 2818 },
  { category: "Refuse", monthly: [446, 210, 6, 283, 286, 582, 312, 307, 302, 277, 570, 201], annualTotal: 3783, comparisonTotal: 2433 },
  { category: "Alarm Maintenance", monthly: [34, 0, 0, 0, 0, 0, 0, 485, 0, 0, 0, 0], annualTotal: 519, comparisonTotal: 519 },
  { category: "Advertising", monthly: [0, 0, 0, 0, 0, 0, 0, 0, 257, 0, 2750, 0], annualTotal: 3007, comparisonTotal: 0 },
  { category: "Staff Training", monthly: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], annualTotal: 0, comparisonTotal: 0 },
  { category: "Pension Fund", monthly: [250, 250, 250, 250, 250, 250, 250, 250, 250, 250, 250, 250], annualTotal: 3000, comparisonTotal: 2000 },
  { category: "Loan", monthly: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], annualTotal: 0, comparisonTotal: 0 },
  { category: "Total", monthly: [23560, 22348, 23914, 23021, 24204, 22900, 19375, 21949, 19843, 17821, 25539, 20715], annualTotal: 265188, comparisonTotal: 181271, kind: "total" },
];

const currencyFormatter = new Intl.NumberFormat("en-GB", {
  style: "currency",
  currency: "GBP",
  maximumFractionDigits: 0,
});

const decimalOneFormatter = new Intl.NumberFormat("en-GB", {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

export function formatCurrency(value: number): string {
  return currencyFormatter.format(value);
}

export function formatOneDecimal(value: number): string {
  return decimalOneFormatter.format(value);
}

const subtotal = OVERHEAD_ROWS.find((row) => row.kind === "subtotal");
const total = OVERHEAD_ROWS.find((row) => row.kind === "total");

export const OVERHEAD_SUMMARY = {
  subtotalAnnual: subtotal?.annualTotal ?? 0,
  annualTotal: total?.annualTotal ?? 0,
  comparisonTotal: total?.comparisonTotal ?? 0,
  annualDelta: (total?.annualTotal ?? 0) - (total?.comparisonTotal ?? 0),
  monthlyAverage: (total?.annualTotal ?? 0) / 12,
};
