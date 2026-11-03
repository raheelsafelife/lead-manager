export function defaultAuthorizationScope(query) {
  if (query.type !== "authorization" || query.active) return query;
  // Explicit status views remain available; an unfiltered request defaults to active clients.
  const statusView = query.status && query.status !== "All";
  return { ...query, active: statusView ? "All" : "Active" };
}

export async function getLeadListSummary(db, where, params, includeHours = false) {
  const hoursColumns = includeHours ? `,
    coalesce(sum(case when leads.authorization_received = 1 then leads.hours else 0 end), 0) as weekly_hours,
    coalesce(sum(case when leads.authorization_received = 1 then leads.monthly_hours else 0 end), 0) as monthly_hours` : "";
  const summary = await db.get(`select count(*) as count ${hoursColumns}
    from leads left join agencies on agencies.id = leads.agency_id
    left join ccus on ccus.id = leads.ccu_id ${where}`, params);
  return {
    total: Number(summary.count),
    ...(includeHours ? { authorizationHours: {
      weekly: Number(summary.weekly_hours),
      monthly: Number(summary.monthly_hours)
    } } : {})
  };
}
