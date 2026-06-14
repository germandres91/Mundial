import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const COLORS = ["#2563eb", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4"];

const RACE_COLORS = [
  "#2563eb", "#ef4444", "#10b981", "#f59e0b", "#8b5cf6",
  "#06b6d4", "#ec4899", "#84cc16", "#f97316", "#14b8a6",
  "#a855f7", "#eab308",
];

const axisProps = {
  stroke: "#94a3b8",
  fontSize: 12,
  tickLine: false,
};

const tooltipStyle = {
  contentStyle: {
    background: "#0f172a",
    border: "1px solid #1e293b",
    borderRadius: 12,
    color: "#e2e8f0",
  },
};

export function BarChartView({ data, dataKey = "value", labelKey = "label", color }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
        <XAxis dataKey={labelKey} {...axisProps} />
        <YAxis {...axisProps} allowDecimals={false} />
        <Tooltip {...tooltipStyle} cursor={{ fill: "rgba(148,163,184,0.08)" }} />
        <Bar dataKey={dataKey} radius={[6, 6, 0, 0]}>
          {data.map((_, i) => (
            <Cell key={i} fill={color || COLORS[i % COLORS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

function RaceTooltip({ active, payload, label, etiquetas }) {
  if (!active || !payload?.length) return null;
  const ordered = [...payload].sort((a, b) => b.value - a.value);
  return (
    <div
      style={{
        background: "#0f172a",
        border: "1px solid #1e293b",
        borderRadius: 12,
        color: "#e2e8f0",
        padding: "8px 12px",
        fontSize: 12,
        maxWidth: 260,
      }}
    >
      <div style={{ marginBottom: 6, fontWeight: 600 }}>
        #{label} · {etiquetas?.[label] || ""}
      </div>
      {ordered.map((p) => (
        <div
          key={p.dataKey}
          style={{ display: "flex", justifyContent: "space-between", gap: 12 }}
        >
          <span style={{ color: p.color }}>{p.dataKey}</span>
          <strong>{p.value}</strong>
        </div>
      ))}
    </div>
  );
}

export function RaceChart({ partidos = [], series = [] }) {
  const etiquetas = {};
  partidos.forEach((m) => {
    etiquetas[m.orden] = m.etiqueta;
  });

  const data = partidos.map((m, i) => {
    const row = { orden: m.orden };
    series.forEach((s) => {
      row[s.nombre] = s.puntos?.[i] ?? null;
    });
    return row;
  });

  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data} margin={{ top: 8, right: 12, left: -16, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
        <XAxis
          dataKey="orden"
          {...axisProps}
          interval="preserveStartEnd"
          minTickGap={24}
          label={{
            value: "Partidos jugados",
            position: "insideBottom",
            offset: -4,
            fill: "#64748b",
            fontSize: 11,
          }}
        />
        <YAxis {...axisProps} allowDecimals={false} />
        <Tooltip content={<RaceTooltip etiquetas={etiquetas} />} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        {series.map((s, i) => (
          <Line
            key={s.participant_id ?? s.nombre}
            type="monotone"
            dataKey={s.nombre}
            stroke={RACE_COLORS[i % RACE_COLORS.length]}
            strokeWidth={2.5}
            dot={false}
            activeDot={{ r: 5 }}
            connectNulls
            isAnimationActive={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

export function LineChartView({ data, dataKey = "value", labelKey = "label" }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
        <XAxis dataKey={labelKey} {...axisProps} />
        <YAxis {...axisProps} allowDecimals={false} />
        <Tooltip {...tooltipStyle} />
        <Legend />
        <Line
          type="monotone"
          dataKey={dataKey}
          name="Puntos"
          stroke="#2563eb"
          strokeWidth={3}
          dot={{ r: 4 }}
          activeDot={{ r: 6 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
