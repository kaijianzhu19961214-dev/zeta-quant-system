import type {
  ArtifactLedgerResponse,
  ExternalPayloadComparisonRequest,
  FactorComparisonReport,
  FactorValidationReviewResponse,
  OpsOverviewResponse,
} from "./types";

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

export async function fetchFactorValidationReview(): Promise<FactorValidationReviewResponse> {
  const response = await fetch(`${API_BASE_PATH}/api/v1/factor-validation/review`, {
    headers: {
      accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`factor validation review request failed with status ${response.status}`);
  }

  return (await response.json()) as FactorValidationReviewResponse;
}

export async function fetchArtifactLedger(): Promise<ArtifactLedgerResponse> {
  const response = await fetch(`${API_BASE_PATH}/api/v1/artifacts/ledger`, {
    headers: {
      accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`artifact ledger request failed with status ${response.status}`);
  }

  return (await response.json()) as ArtifactLedgerResponse;
}

export async function compareExternalPayloads(
  request: ExternalPayloadComparisonRequest,
): Promise<FactorComparisonReport> {
  const response = await fetch(`${API_BASE_PATH}/api/v1/factor-validation/external-payloads/compare`, {
    method: "POST",
    headers: {
      accept: "application/json",
      "content-type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(await buildApiErrorMessage(response, "external payload comparison request failed"));
  }

  return (await response.json()) as FactorComparisonReport;
}

async function buildApiErrorMessage(response: Response, fallbackMessage: string): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string" && payload.detail.length > 0) {
      return payload.detail;
    }
  } catch {
    return `${fallbackMessage} with status ${response.status}`;
  }

  return `${fallbackMessage} with status ${response.status}`;
}
