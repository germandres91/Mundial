import { useMemo } from "react";
import { flagUrl } from "../utils/flags";
import { R32_TO_R16, pairByIndices, pairSequential } from "../utils/bracketPaths";
import { sortKnockoutMatches } from "../utils/knockoutSort";

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
    if (k.ganador) {
      winner = toTeam(k.ganador);
    } else if (k.goles_local > k.goles_visitante) {
      winner = toTeam(k.local);
    } else if (k.goles_visitante > k.goles_local) {
      winner = toTeam(k.visitante);
    }
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

function projectNextRound(prevCards, phaseKey) {
  if (phaseKey === "Octavos de final") {
    return pairByIndices(prevCards, R32_TO_R16);
  }
  return pairSequential(prevCards);
}

function teamPairKey(a, b) {
  if (!a || !b) return null;
  return [a, b].sort().join("|");
}

function findDbMatch(card, dbMatches) {
  const ka = card.a?.equipo;
  const kb = card.b?.equipo;
  if (!ka || !kb) return null;
  const key = teamPairKey(ka, kb);
  return dbMatches.find((m) => teamPairKey(m.local, m.visitante) === key);
}

function mergeProjectedWithDb(projected, dbMatches) {
  return projected.map((proj) => {
    const db = findDbMatch(proj, dbMatches);
    if (db) return matchToCard(db);
    return proj;
  });
}

function buildRounds(knockout) {
  const byPhase = {};
  for (const k of knockout || []) {
    if (!k.fase) continue;
    (byPhase[k.fase] ||= []).push(k);
  }
  for (const phase of Object.keys(byPhase)) {
    byPhase[phase] = sortKnockoutMatches(byPhase[phase]);
  }

  const r32 = byPhase["Dieciseisavos de final"];
  if (!r32?.length) {
    return ROUNDS.map(() => []);
  }

  let prevCards = r32.map((m) => matchToCard(m));
  const rounds = [prevCards];

  for (const { key } of ROUNDS.slice(1)) {
    const projected = projectNextRound(prevCards, key);
    const cards = mergeProjectedWithDb(projected, byPhase[key] || []);
    rounds.push(cards);
    prevCards = cards;
  }

  return rounds;
}

function Flag({ name }) {
  const url = flagUrl(name);
  if (!url) {
    return <span className="h-3.5 w-5 shrink-0 rounded-sm bg-slate-200 dark:bg-slate-700" />;
  }
  return (
    <img
      src={url}
      alt=""
      loading="lazy"
      className="h-3.5 w-5 shrink-0 rounded-sm object-cover ring-1 ring-black/10"
      onError={(e) => {
        e.currentTarget.style.visibility = "hidden";
      }}
    />
  );
}

function TeamRow({ team, score, isWinner, dimmed, leading }) {
  return (
    <div
      className={`flex items-center gap-1.5 px-2 py-1 ${
        isWinner ? "bg-emerald-500/10 font-bold text-emerald-700 dark:text-emerald-300" : ""
      } ${dimmed ? "opacity-45" : ""} ${leading ? "font-semibold" : ""}`}
    >
      {team ? <Flag name={team.equipo} /> : (
        <span className="h-3.5 w-5 shrink-0 rounded-sm bg-slate-200 dark:bg-slate-700" />
      )}
      <span className="min-w-0 flex-1 truncate text-[11px] leading-tight" title={team?.equipo}>
        {team ? team.equipo : "Por definir"}
      </span>
      {score != null && (
        <span
          className={`w-4 shrink-0 text-right text-[11px] tabular-nums ${
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
      {showIn && <span className="tb-line-in" aria-hidden />}
      <div
        className={`tb-card overflow-hidden rounded-lg border bg-white shadow-sm dark:bg-slate-800 ${
          live
            ? "border-rose-500/60 ring-2 ring-rose-500/25"
            : projected
            ? "border-dashed border-slate-300 dark:border-slate-600"
            : "border-slate-200 dark:border-slate-700"
        }`}
      >
        {live && (
          <div className="flex items-center justify-center gap-1 bg-rose-500/15 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wide text-rose-600 dark:text-rose-400">
            <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-rose-500" />
            {minuto || "Vivo"}
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

  const treeHeight = useMemo(() => {
    const n = Math.max(...rounds.map((r) => r.length), 1);
    return Math.max(560, n * 56 + 80);
  }, [rounds]);

  if (!hasKnockout) {
    return (
      <div className="card text-center text-sm text-slate-500">
        El cuadro de eliminatorias se mostrará cuando el administrador publique los
        dieciseisavos de final.
      </div>
    );
  }

  return (
    <div className="card overflow-hidden p-2 sm:p-4">
      {liveCount > 0 && (
        <p className="mb-2 text-center text-xs text-rose-500">
          {liveCount} en vivo · actualización automática
        </p>
      )}

      <p className="tb-pan-hint mb-2 text-center text-[11px] text-slate-400">
        Desliza con el dedo para mover el cuadro ← → ↕
      </p>

      <div className="tb-scroll-wrap">
        <div className="tb-scroll-fade tb-scroll-fade-left" aria-hidden />
        <div className="tb-scroll-fade tb-scroll-fade-right" aria-hidden />
        <div className="tb-scroll">
          <div className="tb" style={{ "--tb-height": `${treeHeight}px` }}>
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

            <div className="tb-col tb-col-champion">
              <div className="tb-col-title">Campeón</div>
              <div className="tb-body flex items-center justify-center">
                <div className="tb-match tb-match-champion">
                  <span className="tb-line-in" aria-hidden />
                  <div className="flex flex-col items-center gap-1.5 rounded-xl border border-amber-400/60 bg-gradient-to-b from-amber-400/20 to-amber-500/5 px-4 py-4 text-center">
                    <span className="text-3xl">🏆</span>
                    {champion ? (
                      <>
                        <Flag name={champion.equipo} />
                        <span className="max-w-[120px] text-xs font-extrabold leading-tight">
                          {champion.equipo}
                        </span>
                      </>
                    ) : (
                      <span className="text-[10px] text-slate-500">Por definir</span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
