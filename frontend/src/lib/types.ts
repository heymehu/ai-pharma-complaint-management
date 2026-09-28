export type ComplaintStatus =
  | "pending"
  | "under_review"
  | "investigation"
  | "capa"
  | "closed";

export type RiskLevel = "low" | "medium" | "high" | "critical";
export type Priority = "low" | "medium" | "high" | "urgent";

export interface ComplaintFormData {
  complaint_source: string;
  customer_name: string;
  email: string;
  phone: string;
  country: string;
  complaint_date: string;
  product_name: string;
  strength: string;
  dosage_form: string;
  batch_number: string;
  manufacturing_date: string;
  expiry_date: string;
  quantity: string;
  summary: string;
  possible_root_cause: string;
  risk_level: string;
  affected_batches: string;
  regulatory_concern: string;
  impact: string;
  confidence_score: number;
  potential_issue: string;
  suggested_test: string;
  recommended_action: string;
  priority: string;
  ai_reasoning: string;
  required_tests: string[];
  missing_information: string[];
  regulatory_implications: string[];
  escalation_level: string;
  risk_category: string;
  deviation_possibility: string;
}

export const emptyForm = (): ComplaintFormData => ({
  complaint_source: "",
  customer_name: "",
  email: "",
  phone: "",
  country: "",
  complaint_date: new Date().toISOString().slice(0, 10),
  product_name: "",
  strength: "",
  dosage_form: "",
  batch_number: "",
  manufacturing_date: "",
  expiry_date: "",
  quantity: "",
  summary: "",
  possible_root_cause: "",
  risk_level: "",
  affected_batches: "",
  regulatory_concern: "",
  impact: "",
  confidence_score: 0,
  potential_issue: "",
  suggested_test: "",
  recommended_action: "",
  priority: "",
  ai_reasoning: "",
  required_tests: [],
  missing_information: [],
  regulatory_implications: [],
  escalation_level: "",
  risk_category: "",
  deviation_possibility: "",
});

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: Date;
}

export interface Complaint {
  id: number;
  complaint_id: string;
  customer_name?: string;
  product_name?: string;
  batch_number?: string;
  summary?: string;
  status: ComplaintStatus;
  priority: Priority;
  risk_level: RiskLevel;
  created_at: string;
}

export interface DashboardStats {
  total_complaints: number;
  open_complaints: number;
  critical_complaints: number;
  resolved: number;
  avg_resolution_days: number;
  by_status: Record<string, number>;
  by_month: { month: string; count: number }[];
  by_risk: Record<string, number>;
}
