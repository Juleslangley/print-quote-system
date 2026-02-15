import Link from "next/link";
import {
  MONTH_LABELS,
  OVERHEAD_ROWS,
  OVERHEAD_SUMMARY,
  formatCurrency,
  formatOneDecimal,
} from "@/lib/adminOverheads";

export default function AdminOverheadsPage() {
  return (
    <div>
      <p><Link href="/admin">← Admin</Link></p>
      <h1>Admin · Overheads</h1>
      <p className="subtle" style={{ marginTop: -12, marginBottom: 18 }}>
        Monthly overhead costs loaded from your provided figures (12 monthly columns + annual totals).
      </p>

      <div className="row section">
        <div className="card col" style={{ minWidth: 220 }}>
          <div className="subtle">Annual overhead total</div>
          <div style={{ fontSize: 26, fontWeight: 700, marginTop: 6 }}>{formatCurrency(OVERHEAD_SUMMARY.annualTotal)}</div>
        </div>
        <div className="card col" style={{ minWidth: 220 }}>
          <div className="subtle">Comparison total</div>
          <div style={{ fontSize: 26, fontWeight: 700, marginTop: 6 }}>{formatCurrency(OVERHEAD_SUMMARY.comparisonTotal)}</div>
        </div>
        <div className="card col" style={{ minWidth: 220 }}>
          <div className="subtle">Annual delta</div>
          <div style={{ fontSize: 26, fontWeight: 700, marginTop: 6 }}>{formatCurrency(OVERHEAD_SUMMARY.annualDelta)}</div>
        </div>
        <div className="card col" style={{ minWidth: 220 }}>
          <div className="subtle">Average per month</div>
          <div style={{ fontSize: 26, fontWeight: 700, marginTop: 6 }}>{formatCurrency(OVERHEAD_SUMMARY.monthlyAverage)}</div>
        </div>
      </div>

      <div className="card">
        <h2 style={{ marginTop: 0 }}>Monthly overhead lines</h2>
        <div style={{ overflowX: "auto" }}>
          <table style={{ borderCollapse: "collapse", width: "100%", fontSize: 13 }}>
            <thead>
              <tr style={{ textAlign: "left", background: "#f5f5f7" }}>
                <th style={{ padding: "8px 10px", borderBottom: "1px solid #ddd", position: "sticky", left: 0, background: "#f5f5f7" }}>Category</th>
                {MONTH_LABELS.map((label) => (
                  <th key={label} style={{ padding: "8px 10px", borderBottom: "1px solid #ddd", minWidth: 95 }}>
                    {label}
                  </th>
                ))}
                <th style={{ padding: "8px 10px", borderBottom: "1px solid #ddd", minWidth: 110 }}>Annual</th>
                <th style={{ padding: "8px 10px", borderBottom: "1px solid #ddd", minWidth: 120 }}>Comparison</th>
                <th style={{ padding: "8px 10px", borderBottom: "1px solid #ddd", minWidth: 90 }}>Extra</th>
              </tr>
            </thead>
            <tbody>
              {OVERHEAD_ROWS.map((row, index) => {
                const highlighted = row.kind === "subtotal" || row.kind === "total";
                const background = row.kind === "total" ? "#e6f0ff" : row.kind === "subtotal" ? "#f7f9ff" : index % 2 === 0 ? "#fff" : "#fafafa";
                return (
                  <tr key={`${row.category}-${index}`} style={{ background }}>
                    <td
                      style={{
                        padding: "7px 10px",
                        borderBottom: "1px solid #eee",
                        fontWeight: highlighted ? 700 : 500,
                        position: "sticky",
                        left: 0,
                        background,
                        zIndex: 1,
                      }}
                    >
                      {row.category}
                    </td>
                    {row.monthly.map((value, monthIndex) => (
                      <td
                        key={`${row.category}-${monthIndex}`}
                        style={{
                          padding: "7px 10px",
                          borderBottom: "1px solid #eee",
                          fontWeight: highlighted ? 600 : 400,
                        }}
                      >
                        {formatCurrency(value)}
                      </td>
                    ))}
                    <td style={{ padding: "7px 10px", borderBottom: "1px solid #eee", fontWeight: highlighted ? 700 : 600 }}>
                      {formatCurrency(row.annualTotal)}
                    </td>
                    <td style={{ padding: "7px 10px", borderBottom: "1px solid #eee", fontWeight: highlighted ? 700 : 600 }}>
                      {formatCurrency(row.comparisonTotal)}
                    </td>
                    <td style={{ padding: "7px 10px", borderBottom: "1px solid #eee", color: "#555" }}>
                      {row.extraValue == null ? "" : formatOneDecimal(row.extraValue)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      <p className="subtle" style={{ marginTop: 12 }}>
        Sub total annual: {formatCurrency(OVERHEAD_SUMMARY.subtotalAnnual)} · Overall annual: {formatCurrency(OVERHEAD_SUMMARY.annualTotal)}
      </p>
    </div>
  );
}
