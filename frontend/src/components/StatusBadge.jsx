import { MATCH_STATUS_LABELS } from "../types";

const STYLES = {
  SCHEDULED: "bg-slate-500/15 text-slate-400",
  LIVE: "bg-rose-500/15 text-rose-400 animate-pulse",
  FINISHED: "bg-emerald-500/15 text-emerald-400",
  POSTPONED: "bg-amber-500/15 text-amber-400",
  CANCELLED: "bg-slate-500/15 text-slate-400 line-through",
};

export default function StatusBadge({ status }) {
  return (
    <span className={`badge ${STYLES[status] || STYLES.SCHEDULED}`}>
      {MATCH_STATUS_LABELS[status] || status}
    </span>
  );
}
