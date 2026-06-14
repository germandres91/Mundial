import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { endpoints } from "../services/api";

const AUTO_REFRESH = 60_000; // refresca datos en vivo cada minuto

export const useDashboard = () =>
  useQuery({
    queryKey: ["dashboard"],
    queryFn: endpoints.dashboard,
    refetchInterval: AUTO_REFRESH,
  });

const LIVE_REFRESH = 30_000; // refresco rápido cuando hay partidos en vivo

export const useMatches = (params) =>
  useQuery({
    queryKey: ["matches", params],
    queryFn: () => endpoints.matches(params),
    // Si hay algún partido en vivo, refresca más seguido para ver el marcador.
    refetchInterval: (query) => {
      const data = query.state.data;
      const hayEnVivo = Array.isArray(data) && data.some((m) => m.estado === "LIVE");
      return hayEnVivo ? LIVE_REFRESH : AUTO_REFRESH;
    },
  });

export const useParticipants = () =>
  useQuery({ queryKey: ["participants"], queryFn: endpoints.participants });

export const useBracket = (participantId) =>
  useQuery({
    queryKey: ["bracket", participantId],
    queryFn: () => endpoints.bracket(participantId),
    refetchInterval: AUTO_REFRESH,
  });

export const usePredictions = (params) =>
  useQuery({
    queryKey: ["predictions", params],
    queryFn: () => endpoints.predictions(params),
    enabled: params?.participant_id != null,
  });

export const useRanking = () =>
  useQuery({
    queryKey: ["ranking"],
    queryFn: endpoints.ranking,
    // Refresca más seguido si hay puntos provisionales (partidos en vivo).
    refetchInterval: (query) => {
      const data = query.state.data;
      const hayEnVivo = Array.isArray(data) && data.some((r) => r.provisional);
      return hayEnVivo ? LIVE_REFRESH : AUTO_REFRESH;
    },
  });

export const useStatsHits = () =>
  useQuery({ queryKey: ["stats", "hits"], queryFn: endpoints.statsHits });

export const useStatsPhases = () =>
  useQuery({ queryKey: ["stats", "phases"], queryFn: endpoints.statsPhases });

export const useStatsRace = () =>
  useQuery({
    queryKey: ["stats", "race"],
    queryFn: endpoints.statsRace,
    refetchInterval: AUTO_REFRESH,
  });

export const useParticipantTop4 = (id) =>
  useQuery({
    queryKey: ["top4", id],
    queryFn: () => endpoints.participantTop4(id),
    enabled: id != null,
  });

export const useParticipantStats = (id) =>
  useQuery({
    queryKey: ["stats", "participant", id],
    queryFn: () => endpoints.participantStats(id),
    enabled: id != null,
  });

export const useRules = () =>
  useQuery({ queryKey: ["rules"], queryFn: endpoints.rules });

export const useAudit = () =>
  useQuery({ queryKey: ["audit"], queryFn: endpoints.audit });

export const useSyncStatus = () =>
  useQuery({
    queryKey: ["syncStatus"],
    queryFn: endpoints.syncStatus,
    refetchInterval: AUTO_REFRESH,
  });

export const useFinalPositions = () =>
  useQuery({ queryKey: ["finalPositions"], queryFn: endpoints.finalPositions });

export const useUsers = () =>
  useQuery({ queryKey: ["users"], queryFn: endpoints.users });

export function useInvalidateAll() {
  const qc = useQueryClient();
  return () =>
    qc.invalidateQueries({
      predicate: (q) =>
        ["dashboard", "matches", "ranking", "stats"].includes(q.queryKey[0]),
    });
}

export function useMutationWithRefresh(mutationFn, options = {}) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn,
    ...options,
    onSuccess: (...args) => {
      qc.invalidateQueries();
      options.onSuccess?.(...args);
    },
  });
}
