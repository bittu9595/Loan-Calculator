export interface FeeRequest {
  amount: number;
  term: number;
}

export interface FeeResponse {
  amount: number;
  term: number;
  fee: number;
  total_repayable: number;
}

export class ApiError extends Error {}

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function calculateFee(request: FeeRequest): Promise<FeeResponse> {
  const response = await fetch(`${API_BASE_URL}/api/fee`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = body?.detail ?? body?.message ?? "Failed to calculate fee";
    throw new ApiError(
      Array.isArray(detail) ? detail.map((d) => d.msg).join(", ") : detail,
    );
  }

  return response.json();
}
