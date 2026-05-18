import bcrypt from "bcryptjs";
import { z } from "zod";

const credentialsSchema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
});

function normalizeEmail(email: string): string {
  return email.trim().toLowerCase();
}

export async function authorizeDemoUser(credentials: Partial<Record<string, unknown>>) {
  const parsed = credentialsSchema.safeParse(credentials);
  if (!parsed.success) {
    return null;
  }

  const configuredEmail = process.env.HOU53_AUTH_EMAIL;
  const passwordHash = process.env.HOU53_AUTH_PASSWORD_HASH;
  if (!configuredEmail || !passwordHash) {
    return null;
  }

  const email = normalizeEmail(parsed.data.email);
  if (email !== normalizeEmail(configuredEmail)) {
    return null;
  }

  const validPassword = await bcrypt.compare(parsed.data.password, passwordHash);
  if (!validPassword) {
    return null;
  }

  return {
    id: email,
    email,
    name: process.env.HOU53_AUTH_DISPLAY_NAME || "Demo User",
  };
}
