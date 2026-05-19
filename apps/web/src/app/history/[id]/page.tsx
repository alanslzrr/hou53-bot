import Link from "next/link";
import type { Route } from "next";
import { notFound, redirect } from "next/navigation";

import { auth } from "@/auth";
import { AppShell } from "@/components/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { formatDateTime, formatUsd } from "@/lib/format";
import { getPredictionForUser } from "@/server/predictions/repository";

type PredictionDetailPageProps = {
  params: Promise<{ id: string }>;
};

export default async function PredictionDetailPage({ params }: PredictionDetailPageProps) {
  const session = await auth();
  if (!session?.user) {
    redirect("/login" as Route);
  }

  const { id } = await params;
  const row = await getPredictionForUser(id, session.user.id);
  if (!row) {
    notFound();
  }
  const readiness = row.parseMetadataJsonb?.readiness;

  return (
    <AppShell userName={session.user.name || session.user.email}>
      <main className="mx-auto grid max-w-7xl grid-cols-1 gap-5 px-4 py-5 lg:grid-cols-[420px_minmax(0,1fr)]">
        <Card>
          <CardHeader>
            <CardTitle>{formatUsd(row.predictedPriceUsdCents / 100)}</CardTitle>
            <CardDescription>{formatDateTime(row.createdAt)}</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div className="flex flex-wrap gap-2">
              <Badge variant="secondary">{row.inputSource}</Badge>
              <Badge variant="outline">{row.modelVersion}</Badge>
              {readiness ? (
                <Badge variant={readiness.level === "strong" ? "default" : "outline"}>
                  {readiness.level} · {readiness.score}/100
                </Badge>
              ) : null}
            </div>
            <p className="text-muted-foreground text-sm">{row.resultJsonb.explanation.natural_language}</p>
            <Separator />
            <div className="flex flex-col gap-3">
              <p className="font-medium text-sm">SHAP drivers</p>
              {row.shapJsonb.map((feature) => (
                <div key={feature.feature} className="flex items-center justify-between gap-3 text-sm">
                  <span className="truncate">{feature.feature}</span>
                  <span className="font-mono">{formatUsd(feature.contribution_usd)}</span>
                </div>
              ))}
            </div>
            <Button variant="outline" asChild>
              <Link href={"/history" as Route}>Back to history</Link>
            </Button>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Structured input</CardTitle>
            <CardDescription>Payload confirmed before prediction.</CardDescription>
          </CardHeader>
          <CardContent>
            <pre className="max-h-[680px] overflow-auto rounded-2xl bg-muted p-4 font-mono text-xs">
              {JSON.stringify(row.inputJsonb, null, 2)}
            </pre>
          </CardContent>
        </Card>
      </main>
    </AppShell>
  );
}
