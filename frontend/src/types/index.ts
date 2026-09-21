// Domain Types for AI Accounts Receivable Automation Platform

export type InvoiceStatus =
  | 'DRAFT'
  | 'PENDING_REVIEW'
  | 'ISSUED'
  | 'PARTIALLY_PAID'
  | 'PAID'
  | 'OVERDUE'
  | 'VOID';

export type AgingBucket =
  | 'CURRENT'
  | 'DAYS_1_30'
  | 'DAYS_31_60'
  | 'DAYS_61_90'
  | 'DAYS_90_PLUS';

export type PaymentMethod =
  | 'ACH'
  | 'WIRE'
  | 'CHECK'
  | 'CREDIT_CARD'
  | 'OTHER';

export type ReminderTone =
  | 'FRIENDLY'
  | 'STANDARD'
  | 'FIRM'
  | 'URGENT';

export type ActivityType =
  | 'REMINDER_SENT'
  | 'MANUAL_NOTE'
  | 'CALL_LOGGED'
  | 'STATUS_CHANGE'
  | 'PAYMENT_APPLIED';

export interface UserProfile {
  username: string;
  role: 'ADMIN' | 'OPERATOR';
  is_active: boolean;
  permissions: string[];
}

export interface Customer {
  id: string;
  name: string;
  email: string;
  phone?: string | null;
  payment_terms_days: number;
  reminder_paused: boolean;
  created_at: string;
  updated_at: string;
  total_invoiced?: string | number | null;
  outstanding_balance?: string | number | null;
}

export interface InvoiceLineItem {
  id?: string;
  invoice_id?: string;
  description: string;
  quantity: number | string;
  unit_price: number | string;
  line_total: number | string;
}

export interface Invoice {
  id: string;
  customer_id: string;
  customer_name?: string;
  invoice_number: string;
  issue_date: string;
  due_date: string;
  currency: string;
  status: InvoiceStatus;
  total_amount: number | string;
  balance_due: number | string;
  document_source_id?: string | null;
  line_items?: InvoiceLineItem[];
  created_at: string;
  updated_at: string;
}

export interface PaymentRecord {
  id: string;
  invoice_id: string;
  amount: number | string;
  payment_date: string;
  payment_method: PaymentMethod;
  reference_number?: string | null;
  notes?: string | null;
  created_at: string;
}

export interface AgingBucketSummary {
  bucket: AgingBucket;
  label: string;
  invoice_count: number;
  total_balance: number | string;
}

export interface DashboardMetrics {
  total_receivables: number | string;
  total_overdue: number | string;
  dso_days: number;
  as_of_date: string;
}

export interface AgingDistribution {
  buckets: Record<string, AgingBucketSummary>;
  total_receivables: number | string;
  total_overdue: number | string;
  dso_days: number;
}

export interface ReminderCadence {
  id: string;
  name: string;
  trigger_offset_days: number;
  reminder_tone: ReminderTone;
  email_subject_template: string;
  email_body_template: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CollectionActivity {
  id: string;
  invoice_id: string;
  customer_id: string;
  activity_type: ActivityType;
  performed_by: string;
  details: Record<string, any>;
  created_at: string;
}

export interface DocumentUploadResponse {
  document_id: string;
  original_filename: string;
  file_size_bytes: number;
  mime_type: string;
  extraction_status: 'QUEUED' | 'PROCESSING' | 'SUCCESS' | 'PARTIAL_SUCCESS' | 'FAILED';
  task_id?: string | null;
}

export interface DocumentImportStatus {
  document_id: string;
  original_filename: string;
  extraction_status: 'QUEUED' | 'PROCESSING' | 'SUCCESS' | 'PARTIAL_SUCCESS' | 'FAILED';
  extracted_data: {
    invoice_number?: string;
    customer_name?: string;
    customer_email?: string;
    issue_date?: string;
    due_date?: string;
    currency?: string;
    total_amount?: number | string;
    line_items?: {
      description: string;
      quantity: number | string;
      unit_price: number | string;
      line_total?: number | string;
    }[];
  };
  error_message?: string | null;
}

export interface CadenceDispatchSummary {
  evaluated_cadences: number;
  scanned_invoices: number;
  dispatched_count: number;
  skipped_paused: number;
  throttled_count: number;
  errors: string[];
}
