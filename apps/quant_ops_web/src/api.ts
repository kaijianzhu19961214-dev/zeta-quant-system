import type { OpsOverviewResponse } from "./types";

const API_BASE_PATH = import.meta.env.VITE_QUANT_OPS_API_BASE_PATH || "/ops-api";

export async function fetchOverview(): Promise<OpsOverviewResponse> {
  const response = await fetch(`${API_BASE_PATH}/api/v1/overview`, {
    headers: {
      accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`overview request failed with status ${response.status}`);
  }

  return (await response.json()) as OpsOverviewResponse;
}
