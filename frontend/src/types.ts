export interface User {
  id: number;
  email: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface ResourceGroup {
  name: string;
  location: string;
}

export interface Issue {
  resource_name: string;
  resource_type: string;
  issue_type: string;
  severity: string;
  explanation: string;
  fix_command: string | null;
}

export interface AnalysisData {
  summary: string;
  issues: Issue[];
  estimated_savings: string;
}

export interface AnalysisResult {
  resource_group: string;
  resource_count: number;
  resources: unknown[];
  analysis: AnalysisData;
}

export interface AnalysisRecord {
  id: number;
  user_id?: number;
  resource_group: string;
  resources_scanned: number;
  issues_found: number;
  estimated_savings: string | null;
  status: string;
  created_at: string;
  analysis_result?: AnalysisResult | { error: string };
}

export interface AnalyzeStartResponse {
  analysis_id: number;
  resource_group: string;
  status: string;
}
