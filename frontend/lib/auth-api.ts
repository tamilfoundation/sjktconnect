const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface UserProfile {
  id: number;
  google_id: string;
  display_name: string;
  avatar_url: string;
  role: "SUPERADMIN" | "MODERATOR" | "USER";
  admin_school: { moe_code: string; name: string } | null;
  points: number;
  is_active: boolean;
  email: string;
  pending_moderation_count?: number;
}

/** Send Google ID token to backend, get/create UserProfile */
export async function syncGoogleAuth(idToken: string): Promise<UserProfile> {
  const res = await fetch(`${API_URL}/api/v1/auth/google/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ id_token: idToken }),
  });
  if (!res.ok) throw new Error("Auth sync failed");
  return res.json();
}

/** Fetch current user profile from backend */
export async function fetchProfile(): Promise<UserProfile | null> {
  try {
    const res = await fetch(`${API_URL}/api/v1/auth/me/`, {
      credentials: "include",
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

/**
 * Flush the Django session cookie. Call BEFORE next-auth's signOut() so
 * fetchMe() returns null to admin-gated UI immediately. Without this,
 * Django session outlives the JWT and EditSchoolLink etc. stay visible.
 * Best-effort: a network failure here doesn't block the JWT sign-out.
 */
export async function logoutDjangoSession(): Promise<void> {
  try {
    await fetch(`${API_URL}/api/v1/auth/logout/`, {
      method: "POST",
      credentials: "include",
    });
  } catch {
    // ignore — JWT sign-out still proceeds in caller
  }
}
