/** User profile — matches Supabase profiles table */
export interface UserProfile {
  id: string;
  email: string;
  display_name: string | null;
  membership_status: string;
  current_belt: string | null;
  stripe_customer_id: string | null;
  stripe_subscription_id: string | null;
  created_at: string;
  updated_at: string;
}

/** Technique progress entry — matches user_progress table */
export interface ProgressEntry {
  technique_key: string;
  status: 'drilling' | 'learned' | 'none';
  updated_at: string;
}

/** Technique note — matches user_notes table */
export interface NoteEntry {
  technique_key: string;
  note_text: string;
  updated_at: string;
}

/** Success log entry — matches success_log table */
export interface SuccessLogEntry {
  technique_key: string;
  logged_at: string;
}

/** User preferences — matches user_preferences table */
export interface UserPreferences {
  user_id: string;
  last_tab: string | null;
  last_selected_node: string | null;
  recent_viewed: string[]; // JSONB
  last_practiced: string | null;
  videos_watched: number;
  current_belt: string | null;
  key_version: number;
}
