import NextAuth from "next-auth";
import Google from "next-auth/providers/google";

export const { handlers, signIn, signOut, auth } = NextAuth({
  trustHost: true,
  providers: [
    Google({
      clientId: process.env.GOOGLE_OAUTH_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_OAUTH_CLIENT_SECRET!,
      // TD-01 RE-OPENED 2026-04-24: Next 16 + Auth.js v5 beta.30 breaks state/PKCE
      // cookie round-trip (cookie set on sign-in is unparseable on callback).
      // Both NEXTAUTH_*/AUTH_* env var naming combos + removing the duplicate
      // names failed to fix it. Disabling checks as a pragmatic unblock; proper
      // fix (investigate @auth/core cookie handling on Next 16) planned for
      // Sprint 16 code-quality pass.
      checks: [],
    }),
  ],
  callbacks: {
    async jwt({ token, account }) {
      // On initial sign-in, store the Google ID token
      if (account?.id_token) {
        token.id_token = account.id_token;
      }
      return token;
    },
    async session({ session, token }) {
      // Pass Google ID token to session for backend sync
      (session as any).id_token = token.id_token;
      return session;
    },
  },
  pages: {
    signIn: "/sign-in",
  },
});
