export interface PlagiarismResponse {
  success: boolean;
  job_id: string;  // Note: using snake_case to match backend
  message?: string;
}

export interface StatusResponse {
  status: "processing" | "analyzed" | "completed" | "failed";
  progress?: number;
  message?: string;
}

export interface Match {
  text_snippet: string;
  source_url: string;
  similarity_score: number;
}

export interface ResultResponse {
  success: boolean;
  plagiarism_percentage: number;
  matches: Match[];
  full_text_with_highlights: string;
  themes: string[];
}