import NextAuth from "next-auth";
import Google from "next-auth/providers/google";

export const { handlers, signIn, signOut, auth } = NextAuth({
  trustHost: true,
  useSecureCookies: false,
  providers: [
    Google({
      clientId: process.env.GOOGLE_OAUTH_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_OAUTH_CLIENT_SECRET!,
      checks: ["state"],
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
