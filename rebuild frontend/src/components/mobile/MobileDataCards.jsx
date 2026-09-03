export default function MobileDataCards({ rows, columns, getKey, emptyTitle = "No data available", emptyText = "Try changing your filters or date range." }) {
  if (!rows.length) {
    return <div className="m-empty"><span aria-hidden="true">—</span><b>{emptyTitle}</b><p>{emptyText}</p></div>;
  }

  return (
    <div className="m-data-list">
      {rows.map((row, index) => (
        <article className="m-data-card" key={getKey ? getKey(row, index) : index}>
          {columns.map((column, columnIndex) => (
            <div className={columnIndex === 0 ? "m-data-primary" : "m-data-field"} key={column.key || column.label}>
              <span>{column.label}</span>
              <b>{column.render ? column.render(row) : row[column.key] ?? "N/A"}</b>
            </div>
          ))}
        </article>
      ))}
    </div>
  );
}
