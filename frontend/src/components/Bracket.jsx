import { useMemo } from "react";
import { flagUrl } from "../utils/flags";

const ROUNDS = [
  { key: "Dieciseisavos de final", title: "Dieciseisavos" },
  { key: "Octavos de final", title: "Octavos" },
  { key: "Cuartos de final", title: "Cuartos" },
  { key: "Semifinales", title: "Semifinales" },
  { key: "Final", title: "Final" },
];

function toTeam(name) {
  if (!name) return null;
  return { equipo: name };
}

function matchToCard(k, { projected = false } = {}) {
  const live = k.estado === "LIVE";
  const finished = k.estado === "FINISHED";
  const hasScore = k.goles_local != null && k.goles_visitante != null;

  let winner = null;
  if (finished && hasScore) {
    if (k.goles_local > k.goles_visitante) winner = toTeam(k.local);
    else if (k.goles_visitante > k.goles_local) winner = toTeam(k.visitante);
  }

  return {
    key: k.fifa_id || k.id || `${k.local}-${k.visitante}`,
    a: toTeam(k.local),
    b: toTeam(k.visitante),
    scoreA: hasScore ? k.goles_local : null,
    scoreB: hasScore ? k.goles_visitante : null,
    winner,
    live,
    minuto: k.minuto,
    projected,
  };
}

function projectNextRound(prevCards) {
  const pairs = [];
  for (let i = 0; i < prevCards.length; i += 2) {
    const a = prevCards[i]?.winner || null;
    const b = prevCards[i + 1]?.winner || null;
    pairs.push({
      key: `proj-${i / 2}`,
      a,
      b,
      scoreA: null,
      scoreB: null,
      winner: null,
      live: false,
      minuto: null,
      projected: true,
    });
  }
  return pairs;
}

function buildRounds(knockout) {
  const byPhase = {};
  for (const k of knockout || []) {
    if (!k.fase) continue;
    (byPhase[k.fase] ||= []).push(k);
  }
  for (const phase of Object.keys(byPhase)) {
    byPhase[phase].sort((a, b) => (a.fifa_id || "").localeCompare(b.fifa_id || ""));
  }

  const rounds = [];
  let prevCards = null;

  for (const { key } of ROUNDS) {
    const db = byPhase[key];
    if (db?.length) {
      const cards = db.map((m) => matchToCard(m));
      rounds.push(cards);
      prevCards = cards;
    } else if (prevCards?.length) {
      const cards = projectNextRound(prevCards);
      rounds.push(cards);
      prevCards = cards;
    } else {
      rounds.push([]);
      prevCards = null;
    }
  }

  return rounds;
}

function Flag({ name }) {
  const url = flagUrl(name);
  if (!url) {
    return <span className="h-4 w-6 shrink-0 rounded-sm bg-slate-200 dark:bg-slate-700" />;
  }
  return (
    <img
      src={url}
      alt=""
      loading="lazy"
      className="h-4 w-6 shrink-0 rounded-sm object-cover ring-1 ring-black/10"
      onError={(e) => {
        e.currentTarget.style.visibility = "hidden";
      }}
    />
  );
}

function TeamRow({ team, score, isWinner, dimmed, leading }) {
  return (
    <div
      className={`flex items-center gap-2 px-2 py-1 ${
        isWinner ? "bg-emerald-500/10 font-bold text-emerald-700 dark:text-emerald-300" : ""
      } ${dimmed ? "opacity-45" : ""} ${leading ? "font-semibold" : ""}`}
    >
      {team ? <Flag name={team.equipo} /> : <span className="h-4 w-6 shrink-0 rounded-sm bg-slate-200 dark:bg-slate-700" />}
      <span className="flex-1 truncate text-xs leading-tight">
        {team ? team.equipo : "Por definir"}
      </span>
      {score != null && (
        <span
          className={`min-w-[1.25rem] text-right text-xs tabular-nums ${
            isWinner ? "font-extrabold" : "font-medium"
          }`}
        >
          {score}
        </span>
      )}
    </div>
  );
}

function MatchCard({ match, showIn }) {
  const { a, b, scoreA, scoreB, winner, live, minuto, projected } = match;
  const aWin = winner && a && winner.equipo === a.equipo;
  const bWin = winner && b && winner.equipo === b.equipo;
  const aLeading =
    live && scoreA != null && scoreB != null && scoreA > scoreB && !winner;
  const bLeading =
    live && scoreA != null && scoreB != null && scoreB > scoreA && !winner;

  return (
    <div className="tb-match">
      {showIn && <span className="tb-line-in" />}
      <div
        className={`tb-card overflow-hidden rounded-lg border bg-white shadow-sm transition-shadow dark:bg-slate-800 ${
          live
            ? "border-rose-500/60 ring-2 ring-rose-500/30 shadow-rose-500/10"
            : projected
            ? "border-dashed border-slate-300 dark:border-slate-600"
            : "border-slate-200 dark:border-slate-700"
        }`}
      >
        {live && (
          <div className="flex items-center justify-center gap-1 bg-rose-500/15 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-rose-600 dark:text-rose-400">
            <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-rose-500" />
            En vivo{minuto ? ` · ${minuto}` : ""}
          </div>
        )}
        <TeamRow team={a} score={scoreA} isWinner={aWin} dimmed={winner && !aWin} leading={aLeading} />
        <div className="border-t border-slate-100 dark:border-slate-700/70" />
        <TeamRow team={b} score={scoreB} isWinner={bWin} dimmed={winner && !bWin} leading={bLeading} />
      </div>
    </div>
  );
}

export default function Bracket({ knockout = [] }) {
  const rounds = useMemo(() => buildRounds(knockout), [knockout]);
  const champion = rounds[rounds.length - 1]?.[0]?.winner || null;
  const hasKnockout = (knockout || []).length > 0;
  const liveCount = (knockout || []).filter((m) => m.estado === "LIVE").length;

  if (!hasKnockout) {
    return (
      <div className="card text-center text-sm text-slate-500">
        El cuadro de eliminatorias se mostrará cuando el administrador publique los
        dieciseisavos de final.
      </div>
    );
  }

  return (
    <div className="card p-3">
      {liveCount > 0 && (
        <p className="mb-2 text-center text-xs text-rose-500">
          {liveCount} partido{liveCount > 1 ? "s" : ""} en vivo — el cuadro se actualiza
          automáticamente
        </p>
      )}
      <div className="tb-scroll">
        <div className="tb">
          {ROUNDS.map((round, ri) => (
            <div key={round.key} className="tb-col">
              <div className="tb-col-title">{round.title}</div>
              <div className="tb-body">
                {(rounds[ri] || []).map((m) => (
                  <MatchCard key={m.key} match={m} showIn={ri > 0} />
                ))}
              </div>
            </div>
          ))}

          <div className="tb-col" style={{ minWidth: 180 }}>
            <div className="tb-col-title">Campeón</div>
            <div className="tb-body flex items-center justify-center">
              <div className="tb-match !flex-none">
                <span className="tb-line-in" />
                <div className="flex flex-col items-center gap-2 rounded-2xl border border-amber-400/60 bg-gradient-to-b from-amber-400/20 to-amber-500/5 px-5 py-5 text-center shadow-inner">
                  <span className="text-4xl">🏆</span>
                  {champion ? (
                    <>
                      <Flag name={champion.equipo} />
                      <span className="text-base font-extrabold">{champion.equipo}</span>
                    </>
                  ) : (
                    <span className="text-xs text-slate-500">Por definir</span>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
