import { redirect } from "next/navigation";
import type { Route } from "next";

import { auth } from "@/auth";
import { AppShell } from "@/components/app-shell";
import { EstimateWorkspace } from "@/features/estimate/estimate-workspace";

export default async function HomePage() {
  const session = await auth();
  if (!session?.user) {
    redirect("/login" as Route);
  }

  return (
    <AppShell userName={session.user.name || session.user.email}>
      <EstimateWorkspace />
    </AppShell>
  );
}
