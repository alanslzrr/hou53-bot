import NextAuth, { type DefaultSession } from "next-auth";
import Credentials from "next-auth/providers/credentials";

import { authorizeDemoUser } from "@/server/auth/credentials";

declare module "next-auth" {
  interface Session {
    user: {
      id: string;
    } & DefaultSession["user"];
  }
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  session: { strategy: "jwt" },
  pages: {
    signIn: "/login",
  },
  providers: [
    Credentials({
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      authorize: authorizeDemoUser,
    }),
  ],
  callbacks: {
    authorized({ auth: session }) {
      return Boolean(session?.user);
    },
    jwt({ token, user }) {
      if (user) {
        (token as { id?: string }).id = user.id;
      }
      return token;
    },
    session({ session, token }) {
      if (session.user) {
        session.user.id = String((token as { id?: string }).id ?? token.sub ?? session.user.email);
      }
      return session;
    },
  },
});
