import Link from "next/link";
import type { Route } from "next";
import { redirect } from "next/navigation";
import { AlertCircleIcon } from "lucide-react";

import { auth } from "@/auth";
import { AppShell } from "@/components/app-shell";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDateTime, formatUsd } from "@/lib/format";
import { listPredictionsForUser } from "@/server/predictions/repository";
import type { PredictionRow } from "@/server/db/schema";

export default async function HistoryPage() {
  const session = await auth();
  if (!session?.user) {
    redirect("/login" as Route);
  }

  let rows: PredictionRow[];
  let error: string | undefined;
  try {
    rows = await listPredictionsForUser(session.user.id);
  } catch (unknownError) {
    rows = [];
    error = unknownError instanceof Error ? unknownError.message : "Prediction history is unavailable.";
  }

  return (
    <AppShell userName={session.user.name || session.user.email}>
      <main className="mx-auto flex max-w-7xl flex-col gap-5 px-4 py-5">
        <Card>
          <CardHeader>
            <CardTitle>Prediction history</CardTitle>
            <CardDescription>Saved valuations for the signed-in demo user.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {error ? (
              <Alert variant="destructive">
                <AlertCircleIcon />
                <AlertTitle>History unavailable</AlertTitle>
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            ) : null}
            {rows.length === 0 && !error ? (
              <div className="flex flex-col gap-3 rounded-2xl border p-6">
                <p className="font-medium">No predictions saved yet.</p>
                <p className="text-muted-foreground text-sm">Run a new estimate to populate this table.</p>
                <Button asChild className="w-fit">
                  <Link href="/">New estimate</Link>
                </Button>
              </div>
            ) : null}
            {rows.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Created</TableHead>
                    <TableHead>Price</TableHead>
                    <TableHead>Source</TableHead>
                    <TableHead>Model</TableHead>
                    <TableHead className="text-right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.map((row) => (
                    <TableRow key={row.id}>
                      <TableCell>{formatDateTime(row.createdAt)}</TableCell>
                      <TableCell className="font-medium">{formatUsd(row.predictedPriceUsdCents / 100)}</TableCell>
                      <TableCell>
                        <Badge variant="secondary">{row.inputSource}</Badge>
                      </TableCell>
                      <TableCell className="font-mono">{row.modelVersion}</TableCell>
                      <TableCell className="text-right">
                        <Button variant="outline" size="sm" asChild>
                          <Link href={`/history/${row.id}` as Route}>Open</Link>
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : null}
          </CardContent>
        </Card>
      </main>
    </AppShell>
  );
}
