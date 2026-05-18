"use client";

import { AlertCircleIcon, CheckCircle2Icon, CircleDotIcon, DatabaseIcon } from "lucide-react";

import { Shimmer } from "@/components/ai-elements/shimmer";
import { Task, TaskContent, TaskItem, TaskTrigger } from "@/components/ai-elements/task";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { formatDateTime, formatUsd } from "@/lib/format";
import type { PredictSuccessResponse } from "@/server/predict/types";

import type { EstimateState } from "./estimate-state";

type ResultPanelProps = {
  state: EstimateState;
  filledCount: number;
  aiFilledCount: number;
  missingCount: number;
  canPredict: boolean;
  onPredict: () => void;
};

function StatusBadge({ state }: { state: EstimateState }) {
  if (state.status === "parsing" || state.status === "predicting") {
    return <Badge variant="secondary">Working</Badge>;
  }
  if (state.status === "predicted") {
    return <Badge variant="default">Predicted</Badge>;
  }
  if (state.status.endsWith("_error")) {
    return <Badge variant="destructive">Needs attention</Badge>;
  }
  if (state.status === "parsed_partial") {
    return <Badge variant="outline">Partial parse</Badge>;
  }
  return <Badge variant="secondary">Ready</Badge>;
}

function WorkflowTask({ state }: { state: EstimateState }) {
  const parsingDone = !["idle", "parsing"].includes(state.status);
  const predictingDone = state.status === "predicted";
  const saved = state.result?.saved;

  return (
    <Task defaultOpen={state.status !== "predicted"}>
      <TaskTrigger title="Workflow status" />
      <TaskContent>
        <TaskItem className="flex items-center gap-2">
          {parsingDone ? <CheckCircle2Icon /> : <CircleDotIcon />}
          Extract and validate fields
        </TaskItem>
        <TaskItem className="flex items-center gap-2">
          {predictingDone ? <CheckCircle2Icon /> : <CircleDotIcon />}
          Estimate price with FastAPI
        </TaskItem>
        <TaskItem className="flex items-center gap-2">
          {saved ? <CheckCircle2Icon /> : <DatabaseIcon />}
          Save confirmed prediction
        </TaskItem>
      </TaskContent>
    </Task>
  );
}

function PriceResult({ result }: { result: PredictSuccessResponse }) {
  return (
    <div className="flex flex-col gap-4">
      <div>
        <p className="text-muted-foreground text-sm">Estimated sale price</p>
        <p className="font-heading text-4xl">{formatUsd(result.prediction.value_usd)}</p>
      </div>
      <p className="text-muted-foreground text-sm">{result.explanation.natural_language}</p>
      <Separator />
      <div className="flex flex-col gap-3">
        <p className="font-medium text-sm">Top SHAP drivers</p>
        {result.explanation.top_features.map((feature) => (
          <div key={feature.feature} className="flex items-center justify-between gap-3 text-sm">
            <span className="truncate">{feature.feature}</span>
            <div className="flex items-center gap-2">
              <Badge variant={feature.direction === "up" ? "secondary" : "outline"}>{feature.direction}</Badge>
              <span className="font-mono">{formatUsd(feature.contribution_usd)}</span>
            </div>
          </div>
        ))}
      </div>
      <Separator />
      <dl className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <dt className="text-muted-foreground">Model</dt>
          <dd className="truncate font-mono">{result.model.version}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Request</dt>
          <dd className="truncate font-mono">{result.api_request_id}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Saved</dt>
          <dd>{result.saved ? "Yes" : "No"}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Created</dt>
          <dd>{formatDateTime(result.created_at)}</dd>
        </div>
      </dl>
      {result.warning ? (
        <Alert>
          <AlertCircleIcon />
          <AlertTitle>Prediction computed</AlertTitle>
          <AlertDescription>{result.warning}</AlertDescription>
        </Alert>
      ) : null}
    </div>
  );
}

export function ResultPanel({ state, filledCount, aiFilledCount, missingCount, canPredict, onPredict }: ResultPanelProps) {
  const busy = state.status === "parsing" || state.status === "predicting";

  return (
    <Card className="sticky top-20">
      <CardHeader>
        <div className="flex items-center justify-between gap-3">
          <CardTitle>Estimate summary</CardTitle>
          <StatusBadge state={state} />
        </div>
        <CardDescription>{filledCount} fields filled · {aiFilledCount} AI-filled · {missingCount} missing hints</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        {busy ? <Shimmer>{state.status === "parsing" ? "Extracting fields" : "Estimating price"}</Shimmer> : null}
        <WorkflowTask state={state} />
        {state.parseError ? (
          <Alert variant="destructive">
            <AlertCircleIcon />
            <AlertTitle>Parse failed</AlertTitle>
            <AlertDescription>{state.parseError.message}</AlertDescription>
          </Alert>
        ) : null}
        {state.predictError ? (
          <Alert variant="destructive">
            <AlertCircleIcon />
            <AlertTitle>Prediction failed</AlertTitle>
            <AlertDescription>{state.predictError.message}</AlertDescription>
          </Alert>
        ) : null}
        {state.result ? <PriceResult result={state.result} /> : null}
        <Button onClick={onPredict} disabled={!canPredict || state.status === "predicting"}>
          {state.status === "predicting" ? "Estimating..." : "Predict price"}
        </Button>
      </CardContent>
    </Card>
  );
}
