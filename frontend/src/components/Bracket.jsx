import { useMemo } from "react";
import { flagUrl } from "../utils/flags";

const ROUNDS = [
  { key: "Dieciseisavos de final", title: "Dieciseisavos", short: "R32" },
  { key: "Octavos de final", title: "Octavos", short: "R16" },
  { key: "Cuartos de final", title: "Cuartos", short: "QF" },
  { key: "Semifinales", title: "Semifinales", short: "SF" },
  { key: "Final", title: "Final", short: "F" },
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
    pairs.push({
      key: `proj-${i / 2}`,
      a: prevCards[i]?.winner || null,
      b: prevCards[i + 1]?.winner || null,
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

function Flag({ name, size = "md" }) {
  const url = flagUrl(name);
  const cls =
    size === "sm"
      ? "h-3.5 w-5 shrink-0 rounded-sm"
      : "h-4 w-6 shrink-0 rounded-sm";
  if (!url) {
    return <span className={`${cls} bg-slate-200 dark:bg-slate-700`} />;
  }
  return (
    <img
      src={url}
      alt=""
      loading="lazy"
      className={`${cls} object-cover ring-1 ring-black/10`}
      onError={(e) => {
        e.currentTarget.style.visibility = "hidden";
      }}
    />
  );
}

function cardShellClass({ live, projected }) {
  if (live) {
    return "border-rose-500/60 ring-2 ring-rose-500/25 shadow-md shadow-rose-500/10";
  }
  if (projected) {
    return "border-dashed border-slate-300 dark:border-slate-600";
  }
  return "border-slate-200 dark:border-slate-700";
}

function LiveBadge({ minuto }) {
  return (
    <div className="flex items-center justify-center gap-1 bg-rose-500/15 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-rose-600 dark:text-rose-400">
      <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-rose-500" />
      En vivo{minuto ? ` · ${minuto}` : ""}
    </div>
  );
}

function TeamRow({ team, score, isWinner, dimmed, leading, compact }) {
  return (
    <div
      className={`flex items-center gap-2 px-2.5 py-1.5 ${
        isWinner ? "bg-emerald-500/10 font-bold text-emerald-700 dark:text-emerald-300" : ""
      } ${dimmed ? "opacity-45" : ""} ${leading ? "font-semibold" : ""}`}
    >
      {team ? <Flag name={team.equipo} size={compact ? "sm" : "md"} /> : (
        <span className="h-4 w-6 shrink-0 rounded-sm bg-slate-200 dark:bg-slate-700" />
      )}
      <span
        className={`flex-1 leading-tight text-slate-800 dark:text-slate-100 ${
          compact ? "truncate text-[11px]" : "text-xs sm:text-sm"
        }`}
        title={team?.equipo}
      >
        {team ? team.equipo : "Por definir"}
      </span>
      {score != null && (
        <span
          className={`min-w-[1.25rem] text-right tabular-nums ${
            compact ? "text-[11px]" : "text-xs"
          } ${isWinner ? "font-extrabold" : "font-medium"}`}
        >
          {score}
        </span>
      )}
    </div>
  );
}

function MatchCardContent({ match, compact = false }) {
  const { a, b, scoreA, scoreB, winner, live, minuto, projected } = match;
  const aWin = winner && a && winner.equipo === a.equipo;
  const bWin = winner && b && winner.equipo === b.equipo;
  const aLeading =
    live && scoreA != null && scoreB != null && scoreA > scoreB && !winner;
  const bLeading =
    live && scoreA != null && scoreB != null && scoreB > scoreA && !winner;

  return (
    <div
      className={`overflow-hidden rounded-lg border bg-white shadow-sm dark:bg-slate-800 ${cardShellClass(
        { live, projected }
      )}`}
    >
      {live && <LiveBadge minuto={minuto} />}
      <TeamRow
        team={a}
        score={scoreA}
        isWinner={aWin}
        dimmed={winner && !aWin}
        leading={aLeading}
        compact={compact}
      />
      <div className="border-t border-slate-100 dark:border-slate-700/70" />
      <TeamRow
        team={b}
        score={scoreB}
        isWinner={bWin}
        dimmed={winner && !bWin}
        leading={bLeading}
        compact={compact}
      />
    </div>
  );
}

function TreeMatchCard({ match, showIn }) {
  return (
    <div className="tb-match">
      {showIn && <span className="tb-line-in" aria-hidden />}
      <div className="tb-card">
        <MatchCardContent match={match} compact />
      </div>
    </div>
  );
}

/** Vista móvil: rondas apiladas, tarjetas legibles a ancho completo. */
function BracketMobile({ rounds, champion, liveCount }) {
  return (
    <div className="space-y-5 md:hidden">
      {liveCount > 0 && (
        <p className="text-center text-xs font-medium text-rose-500">
          {liveCount} partido{liveCount > 1 ? "s" : ""} en vivo
        </p>
      )}

      {ROUNDS.map((round, ri) => {
        const cards = rounds[ri] || [];
        if (!cards.length) return null;
        const liveInRound = cards.filter((m) => m.live).length;

        return (
          <section key={round.key} className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <h3 className="text-sm font-bold text-slate-700 dark:text-slate-200">
                {round.title}
              </h3>
              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-500 dark:bg-slate-800">
                {round.short}
                {liveInRound > 0 && (
                  <span className="ml-1 text-rose-500">· {liveInRound} vivo</span>
                )}
              </span>
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              {cards.map((m) => (
                <MatchCardContent key={m.key} match={m} />
              ))}
            </div>
          </section>
        );
      })}

      <section className="rounded-2xl border border-amber-400/50 bg-gradient-to-b from-amber-400/15 to-amber-500/5 p-5 text-center">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-amber-700/80 dark:text-amber-300/80">
          Campeón del mundo
        </p>
        <span className="text-4xl">🏆</span>
        {champion ? (
          <div className="mt-2 flex flex-col items-center gap-2">
            <Flag name={champion.equipo} />
            <p className="text-lg font-extrabold">{champion.equipo}</p>
          </div>
        ) : (
          <p className="mt-2 text-sm text-slate-500">Por definir</p>
        )}
      </section>
    </div>
  );
}

/** Vista escritorio: árbol clásico con scroll horizontal. */
function BracketTree({ rounds, champion, treeHeight }) {
  return (
    <div className="tb-scroll-wrap hidden md:block">
      <p className="tb-scroll-hint mb-2 text-center text-[11px] text-slate-400">
        Desliza horizontalmente para ver todas las rondas →
      </p>
      <div className="tb-scroll">
        <div className="tb" style={{ "--tb-height": `${treeHeight}px` }}>
          {ROUNDS.map((round, ri) => (
            <div key={round.key} className="tb-col">
              <div className="tb-col-title">{round.title}</div>
              <div className="tb-body">
                {(rounds[ri] || []).map((m) => (
                  <TreeMatchCard key={m.key} match={m} showIn={ri > 0} />
                ))}
              </div>
            </div>
          ))}

          <div className="tb-col tb-col-champion">
            <div className="tb-col-title">Campeón</div>
            <div className="tb-body flex items-center justify-center">
              <div className="tb-match tb-match-champion">
                <span className="tb-line-in" aria-hidden />
                <div className="flex flex-col items-center gap-2 rounded-2xl border border-amber-400/60 bg-gradient-to-b from-amber-400/20 to-amber-500/5 px-5 py-5 text-center shadow-inner">
                  <span className="text-4xl">🏆</span>
                  {champion ? (
                    <>
                      <Flag name={champion.equipo} />
                      <span className="max-w-[140px] text-sm font-extrabold leading-tight">
                        {champion.equipo}
                      </span>
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

export default function Bracket({ knockout = [] }) {
  const rounds = useMemo(() => buildRounds(knockout), [knockout]);
  const champion = rounds[rounds.length - 1]?.[0]?.winner || null;
  const hasKnockout = (knockout || []).length > 0;
  const liveCount = (knockout || []).filter((m) => m.estado === "LIVE").length;

  const treeHeight = useMemo(() => {
    const n = Math.max(...rounds.map((r) => r.length), 1);
    return Math.max(520, n * 62 + 72);
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
    <div className="card overflow-hidden p-3 sm:p-4">
      {liveCount > 0 && (
        <p className="mb-3 hidden text-center text-xs text-rose-500 md:block">
          {liveCount} partido{liveCount > 1 ? "s" : ""} en vivo — actualización automática
        </p>
      )}

      <BracketMobile rounds={rounds} champion={champion} liveCount={liveCount} />
      <BracketTree rounds={rounds} champion={champion} treeHeight={treeHeight} />
    </div>
  );
}
