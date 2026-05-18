import Link from "next/link";
import type { Route } from "next";
import { HomeIcon, HistoryIcon, LogOutIcon } from "lucide-react";

import { signOut } from "@/auth";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

type AppShellProps = {
  userName?: string | null;
  children: React.ReactNode;
};

export function AppShell({ userName, children }: AppShellProps) {
  return (
    <div className="min-h-svh bg-background text-foreground">
      <header className="sticky top-0 border-border/80 border-b bg-background/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-3 px-4 py-3">
          <Link href="/" className="flex items-center gap-2 font-heading font-bold text-lg">
            HOU53
          </Link>
          <nav className="flex items-center gap-2">
            <Button variant="ghost" size="sm" asChild>
              <Link href="/">
                <HomeIcon data-icon="inline-start" />
                New
              </Link>
            </Button>
            <Button variant="ghost" size="sm" asChild>
              <Link href={"/history" as Route}>
                <HistoryIcon data-icon="inline-start" />
                History
              </Link>
            </Button>
            <Separator orientation="vertical" className="hidden h-6 sm:block" />
            <span className="hidden max-w-40 truncate text-muted-foreground text-sm sm:block">{userName}</span>
            <form
              action={async () => {
                "use server";
                await signOut({ redirectTo: "/login" });
              }}
            >
              <Button variant="outline" size="sm" type="submit">
                <LogOutIcon data-icon="inline-start" />
                Sign out
              </Button>
            </form>
          </nav>
        </div>
      </header>
      {children}
    </div>
  );
}
