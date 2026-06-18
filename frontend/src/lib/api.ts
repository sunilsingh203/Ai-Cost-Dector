import type {
  AnalysisRecord,
  AnalyzeStartResponse,
  AuthResponse,
  ResourceGroup,
} from "../types";

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const WS_BASE = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000";

function getToken(): string | null {
  return localStorage.getItem("token");
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = body.detail ?? response.statusText;
    throw new Error(
      typeof detail === "string" ? detail : JSON.stringify(detail),
    );
  }

  return response.json() as Promise<T>;
}

export function connectProgressSocket(
  analysisId: number,
  onMessage: (message: string) => void,
  onClose?: () => void,
): WebSocket {
  const token = getToken();
  const url = new URL(`${WS_BASE}/ws/progress/${analysisId}`);
  if (token) {
    url.searchParams.set("token", token);
  }

  const socket = new WebSocket(url.toString());

  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data) as { message: string };
      onMessage(data.message);
    } catch {
      onMessage(String(event.data));
    }
  };

  socket.onclose = () => onClose?.();

  return socket;
}

export const api = {
  signup: (email: string, password: string) =>
    request<AuthResponse>("/api/auth/signup", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  login: (email: string, password: string) =>
    request<AuthResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  getResourceGroups: () =>
    request<{ resource_groups: ResourceGroup[] }>("/api/resource-groups"),

  startAnalysis: (resourceGroup: string) =>
    request<AnalyzeStartResponse>("/api/analyze", {
      method: "POST",
      body: JSON.stringify({ resource_group: resourceGroup }),
    }),

  getAnalysis: (analysisId: number) =>
    request<AnalysisRecord>(`/api/analyses/${analysisId}`),

  getHistory: () => request<{ history: AnalysisRecord[] }>("/api/history"),
};
