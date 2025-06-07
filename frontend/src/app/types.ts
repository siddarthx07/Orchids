// Types for the website cloning application

export type CloneStatus = "idle" | "pending" | "scraping" | "cloning" | "completed" | "failed";

export interface CloneResult {
  request_id: string;
  status: CloneStatus;
  url: string;
  cloned_html?: string;
  error?: string;
  metadata?: Record<string, any>;
}

export interface CloneRequest {
  url: string;
  options?: Record<string, any>;
}
