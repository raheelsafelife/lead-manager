function SkeletonBlock({ className = "", style }) {
  return <span className={`skeleton-block ${className}`} style={style} aria-hidden="true" />;
}

function SkeletonLine({ width = "100%", className = "" }) {
  return <SkeletonBlock className={`skeleton-line ${className}`} style={{ width }} />;
}

function SkeletonStatGrid({ count = 3 }) {
  return (
    <div className="skeleton-stat-grid">
      {Array.from({ length: count }).map((_, index) => (
        <div className="skeleton-stat-card" key={index}>
          <SkeletonLine width="46%" />
          <SkeletonLine width="72%" className="short" />
        </div>
      ))}
    </div>
  );
}

function SkeletonChartCard({ variant = "bar" }) {
  const bars = variant === "horizontal" ? 8 : 6;
  return (
    <div className="skeleton-card skeleton-chart-card">
      <div className="skeleton-card-head">
        <div>
          <SkeletonLine width="180px" />
          <SkeletonLine width="98px" className="short" />
        </div>
        <SkeletonBlock className="skeleton-chip" />
      </div>
      {variant === "donut" ? (
        <div className="skeleton-donut-layout">
          <SkeletonBlock className="skeleton-donut" />
          <div className="skeleton-legend">
            {Array.from({ length: 5 }).map((_, index) => <SkeletonLine key={index} width={`${86 - index * 8}%`} />)}
          </div>
        </div>
      ) : (
        <div className={`skeleton-bars ${variant}`}>
          {Array.from({ length: bars }).map((_, index) => (
            <SkeletonBlock
              key={index}
              className="skeleton-bar"
              style={variant === "horizontal" ? { width: `${92 - index * 8}%` } : { height: `${74 - index * 7}%` }}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function SkeletonLeadRow() {
  return (
    <div className="skeleton-lead-row">
      <div className="skeleton-lead-main">
        <SkeletonLine width="36%" />
        <SkeletonLine width="22%" className="short" />
      </div>
      <div className="skeleton-status-card">
        <SkeletonLine width="72%" />
        <SkeletonLine width="54%" className="short" />
      </div>
    </div>
  );
}

export function SkeletonTable({ rows = 6, columns = 4 }) {
  return (
    <div className="skeleton-card skeleton-table-card">
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div className="skeleton-table-row" key={rowIndex}>
          {Array.from({ length: columns }).map((_, columnIndex) => (
            <SkeletonLine key={columnIndex} width={columnIndex === 0 ? "48%" : "76%"} />
          ))}
        </div>
      ))}
    </div>
  );
}

export function AppRouteSkeleton() {
  return (
    <div className="skeleton-page route-skeleton">
      <SkeletonLine width="260px" className="skeleton-title" />
      <SkeletonLine width="420px" />
      <SkeletonStatGrid count={3} />
    </div>
  );
}

export function DashboardSkeleton() {
  return (
    <div className="dashboard-page skeleton-page">
      <section className="dashboard-hero skeleton-hero">
        <SkeletonLine width="min(520px, 80%)" className="skeleton-title" />
        <SkeletonLine width="min(440px, 70%)" />
        <SkeletonBlock className="skeleton-search" />
      </section>
      <SkeletonStatGrid count={3} />
      <div className="chart-grid dashboard-primary-grid">
        <SkeletonChartCard variant="horizontal" />
        <SkeletonChartCard variant="donut" />
      </div>
      <div className="chart-grid">
        <SkeletonChartCard variant="horizontal" />
        <SkeletonChartCard variant="horizontal" />
      </div>
    </div>
  );
}

export function LeadListSkeleton({ rows = 5 }) {
  return (
    <div className="skeleton-lead-list" aria-label="Loading leads">
      {Array.from({ length: rows }).map((_, index) => <SkeletonLeadRow key={index} />)}
    </div>
  );
}

export function ReportsSkeleton() {
  return (
    <div className="reports-page skeleton-page">
      <div className="reports-page-head">
        <SkeletonLine width="160px" />
        <SkeletonLine width="260px" className="skeleton-title" />
        <SkeletonLine width="520px" />
      </div>
      <div className="skeleton-card skeleton-report-controls">
        {Array.from({ length: 5 }).map((_, index) => <SkeletonBlock key={index} className="skeleton-control" />)}
      </div>
      <SkeletonStatGrid count={4} />
      <div className="reports-analysis-grid">
        <SkeletonTable rows={6} columns={4} />
        <SkeletonChartCard variant="donut" />
      </div>
    </div>
  );
}

export function DiscoverySkeleton() {
  return (
    <div className="skeleton-page">
      <SkeletonLine width="280px" className="skeleton-title" />
      <div className="filter-grid">
        <SkeletonBlock className="skeleton-control" />
        <SkeletonBlock className="skeleton-control" />
      </div>
      <SkeletonChartCard variant="horizontal" />
    </div>
  );
}

export function WorkflowSkeleton() {
  return (
    <div className="skeleton-page">
      <SkeletonLine width="300px" className="skeleton-title" />
      <SkeletonStatGrid count={2} />
      <SkeletonTable rows={5} columns={3} />
    </div>
  );
}
