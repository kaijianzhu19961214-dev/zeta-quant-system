import type {
  AlgorithmPromotionReadinessResponse,
  AlgorithmReviewGateEvidenceListResponse,
  AlgorithmSpec,
  ArtifactLedgerResponse,
  ExternalPayloadComparisonPreviewResponse,
  ExternalPayloadComparisonRequest,
  FactorCalculationResponse,
  FactorComparisonReport,
  FactorValidationReviewResponse,
  MarketDataBarsSampleRequest,
  MarketDataBarsSampleResponse,
  MarketDataPriceModeOverview,
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

export async function fetchMarketDataPriceModes(): Promise<MarketDataPriceModeOverview> {
  const response = await fetch(`${API_BASE_PATH}/api/v1/market-data/price-modes`, {
    headers: {
      accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(await buildApiErrorMessage(response, "market data price mode request failed"));
  }

  return (await response.json()) as MarketDataPriceModeOverview;
}

export async function fetchMarketDataBarsSample(
  request: MarketDataBarsSampleRequest,
): Promise<MarketDataBarsSampleResponse> {
  const response = await fetch(`${API_BASE_PATH}/api/v1/market-data/bars/sample`, {
    method: "POST",
    headers: {
      accept: "application/json",
      "content-type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(await buildApiErrorMessage(response, "market data sample request failed"));
  }

  return (await response.json()) as MarketDataBarsSampleResponse;
}

export async function fetchFactorLabAlgorithms(): Promise<AlgorithmSpec[]> {
  const response = await fetch(`${API_BASE_PATH}/api/v1/factor-lab/algorithms`, {
    headers: {
      accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(await buildApiErrorMessage(response, "factor lab algorithms request failed"));
  }

  return (await response.json()) as AlgorithmSpec[];
}

export async function fetchFactorLabMomentumSample(): Promise<FactorCalculationResponse> {
  const response = await fetch(`${API_BASE_PATH}/api/v1/factor-lab/factors/samples/momentum-1d`, {
    headers: {
      accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(await buildApiErrorMessage(response, "factor lab momentum sample request failed"));
  }

  return (await response.json()) as FactorCalculationResponse;
}

export async function fetchAlgorithmReviewGateEvidence(
  algorithmId: string,
): Promise<AlgorithmReviewGateEvidenceListResponse> {
  const response = await fetch(
    `${API_BASE_PATH}/api/v1/factor-lab/algorithms/${encodeURIComponent(algorithmId)}/review-gates/evidence`,
    {
      headers: {
        accept: "application/json",
      },
    },
  );

  if (!response.ok) {
    throw new Error(await buildApiErrorMessage(response, "algorithm review gate evidence request failed"));
  }

  return (await response.json()) as AlgorithmReviewGateEvidenceListResponse;
}

export async function fetchAlgorithmPromotionReadiness(
  algorithmId: string,
): Promise<AlgorithmPromotionReadinessResponse> {
  const response = await fetch(
    `${API_BASE_PATH}/api/v1/factor-lab/algorithms/${encodeURIComponent(algorithmId)}/promotion/readiness`,
    {
      headers: {
        accept: "application/json",
      },
    },
  );

  if (!response.ok) {
    throw new Error(await buildApiErrorMessage(response, "algorithm promotion readiness request failed"));
  }

  return (await response.json()) as AlgorithmPromotionReadinessResponse;
}

export async function fetchExternalPayloadComparisonPreview(): Promise<ExternalPayloadComparisonPreviewResponse> {
  const response = await fetch(`${API_BASE_PATH}/api/v1/factor-validation/external-payloads/preview`, {
    headers: {
      accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(await buildApiErrorMessage(response, "external payload comparison preview failed"));
  }

  return (await response.json()) as ExternalPayloadComparisonPreviewResponse;
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
