// Lightweight pub/sub for "the Django session is now ready" — fires after
// UserMenu's syncGoogleAuth() POST to /api/v1/auth/google/ resolves and the
// Django session cookie is set. Auth-aware components (EditSchoolLink,
// SuggestButton) listen and re-fetch /me, because their first fetch raced
// the cookie write and returned null. (TD-18)
//
// Module-scoped Set, not a React context, so non-tree consumers can wire in
// without forcing a Provider above every component that needs auth.

type Listener = () => void;

const listeners = new Set<Listener>();

export function emitProfileReady(): void {
  listeners.forEach((fn) => {
    try {
      fn();
    } catch {
      // a buggy listener shouldn't kill the rest
    }
  });
}

export function onProfileReady(fn: Listener): () => void {
  listeners.add(fn);
  return () => {
    listeners.delete(fn);
  };
}
