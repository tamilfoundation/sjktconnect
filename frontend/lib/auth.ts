import NextAuth from "next-auth";
import Google from "next-auth/providers/google";

const useSecureCookies = process.env.NODE_ENV === "production";
const cookiePrefix = useSecureCookies ? "__Secure-" : "";

export const { handlers, signIn, signOut, auth } = NextAuth({
  trustHost: true,
  // Override @auth/core's defaults so the CSRF cookie uses __Secure- instead of
  // __Host-. The __Host- prefix forbids a Domain attribute and requires Path=/
  // from a secure origin; Cloudflare's proxy / Cloud Run header pipeline has
  // historically modified Set-Cookie in ways that violate __Host- semantics,
  // which silently drops the cookie at the browser. Auth.js then reads back a
  // missing/garbled state value on callback (TD-01: "InvalidCheck: state value
  // could not be parsed"). __Secure- is one notch less strict and survives the
  // proxy; PKCE + state checks remain enforced.
  cookies: {
    csrfToken: {
      name: `${cookiePrefix}authjs.csrf-token`,
      options: {
        httpOnly: true,
        sameSite: "lax",
        path: "/",
        secure: useSecureCookies,
      },
    },
  },
  providers: [
    Google({
      clientId: process.env.GOOGLE_OAUTH_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_OAUTH_CLIENT_SECRET!,
      checks: ["pkce", "state"],
    }),
  ],
  callbacks: {
    async jwt({ token, account }) {
      if (account?.id_token) {
        token.id_token = account.id_token;
      }
      return token;
    },
    async session({ session, token }) {
      (session as any).id_token = token.id_token;
      return session;
    },
  },
  pages: {
    signIn: "/sign-in",
  },
});
