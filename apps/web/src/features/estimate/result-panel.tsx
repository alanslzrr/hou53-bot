"use client";

import { AlertCircleIcon, CheckCircle2Icon, CircleDotIcon, DatabaseIcon } from "lucide-react";

import { InfoTooltip } from "@/components/info-tooltip";
import { Shimmer } from "@/components/ai-elements/shimmer";
import { Task, TaskContent, TaskItem, TaskTrigger } from "@/components/ai-elements/task";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { formatDateTime, formatUsd } from "@/lib/format";
import { getModelFeatureCopy, humanizeExplanationText } from "@/lib/housing/feature-copy";
import type { HouseFeatureName, HouseFieldValue } from "@/lib/housing/schema";
import type { ReadinessErrorResponse, ReadinessQuestion, ReadinessSuccessResponse } from "@/lib/readiness/types";
import type { PredictSuccessResponse } from "@/server/predict/types";

import type { EstimateState } from "./estimate-state";
import type { PredictionSignal } from "./prediction-signal";
import { ReadinessAssistantPanel, type ReadinessAnswerValues } from "./readiness-assistant-panel";

type ResultPanelProps = {
  state: EstimateState;
  filledCount: number;
  aiFilledCount: number;
  predictionSignal: PredictionSignal;
  readiness?: ReadinessSuccessResponse;
  readinessAnswers: ReadinessAnswerValues;
  onReadinessAnswerChange: (fieldName: HouseFeatureName, value: HouseFieldValue | undefined) => void;
  onReadinessQuickAnswer: (question: ReadinessQuestion, value: string) => void;
  onApplyReadinessAnswers: () => void;
  onPredictSparse: () => void;
  canPredict: boolean;
  onPredict: () => void;
  onReset: () => void;
};

function StatusBadge({ state }: { state: EstimateState }) {
  if (["parsing", "assessing", "applying_answers", "predicting"].includes(state.status)) {
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
  const assessingDone = !["idle", "parsing", "parsed_partial", "parsed_valid", "editing", "assessing"].includes(state.status);
  const improveDone = state.status === "predicting" || state.status === "predicted";
  const predictingDone = state.status === "predicted";
  const saved = state.result?.saved;
  const active = ["parsing", "assessing", "applying_answers", "predicting"].includes(state.status);

  return (
    <Task defaultOpen={active}>
      <TaskTrigger title="Workflow status" />
      <TaskContent>
        <TaskItem className="flex items-center gap-2">
          {parsingDone ? <CheckCircle2Icon /> : <CircleDotIcon />}
          Extract and validate fields
        </TaskItem>
        <TaskItem className="flex items-center gap-2">
          {assessingDone ? <CheckCircle2Icon /> : <CircleDotIcon />}
          Assess input signal
        </TaskItem>
        <TaskItem className="flex items-center gap-2">
          {improveDone ? <CheckCircle2Icon /> : <CircleDotIcon />}
          Improve sparse fields
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
  const topFeatureNames = result.explanation.top_features.map((feature) => feature.feature);

  return (
    <div className="flex flex-col gap-4">
      <div>
        <p className="text-muted-foreground text-sm">Estimated sale price</p>
        <p className="font-heading text-4xl">{formatUsd(result.prediction.value_usd)}</p>
      </div>
      <p className="text-muted-foreground text-sm">
        {humanizeExplanationText(result.explanation.natural_language, topFeatureNames)}
      </p>
      <Separator />
      <div className="flex flex-col gap-3">
        <p className="font-medium text-sm">Top SHAP drivers</p>
        {result.explanation.top_features.map((feature) => {
          const copy = getModelFeatureCopy(feature.feature);

          return (
            <div key={feature.feature} className="flex items-center justify-between gap-3 text-sm">
              <span className="flex min-w-0 items-center gap-1.5">
                <span className="truncate">{copy.label}</span>
                <InfoTooltip label={`What is ${copy.label}?`}>{copy.description}</InfoTooltip>
              </span>
              <div className="flex shrink-0 items-center gap-2">
                <Badge variant={feature.direction === "up" ? "secondary" : "outline"}>{feature.direction}</Badge>
                <span className="font-mono">{formatUsd(feature.contribution_usd)}</span>
              </div>
            </div>
          );
        })}
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

export function ResultPanel({
  state,
  filledCount,
  aiFilledCount,
  predictionSignal,
  readiness,
  readinessAnswers,
  onReadinessAnswerChange,
  onReadinessQuickAnswer,
  onApplyReadinessAnswers,
  onPredictSparse,
  canPredict,
  onPredict,
  onReset,
}: ResultPanelProps) {
  const busy = state.status === "parsing" || state.status === "assessing" || state.status === "predicting";
  const assessing = state.status === "assessing";
  const signalLabel = predictionSignal.ready ? "model signal ready" : `${predictionSignal.missingSignals.length} signal gaps`;
  const readinessError = state.readinessError as ReadinessErrorResponse["error"] | undefined;
  const hasAnyInput = filledCount > 0;
  const isPredicted = state.status === "predicted";
  const primaryLabel = isPredicted
    ? "Start new estimate"
    : state.status === "predicting"
      ? "Estimating..."
      : assessing
        ? "Assessing..."
        : predictionSignal.ready
          ? "Predict price"
          : "Improve estimate";

  return (
    <Card className="overflow-visible">
      <CardHeader>
        <div className="flex items-center justify-between gap-3">
          <CardTitle>Estimate summary</CardTitle>
          <StatusBadge state={state} />
        </div>
        <CardDescription>
          {filledCount} fields filled · {aiFilledCount} AI-filled · {signalLabel}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        {busy ? (
          <Shimmer>
            {state.status === "parsing"
              ? "Extracting fields"
              : state.status === "assessing"
                ? "Assessing input signal"
                : "Estimating price"}
          </Shimmer>
        ) : null}
        {state.result ? <PriceResult result={state.result} /> : null}
        {readiness && readiness.questions.length > 0 && !state.result ? (
          <ReadinessAssistantPanel
            readiness={readiness}
            answers={readinessAnswers}
            onAnswerChange={onReadinessAnswerChange}
            onQuickAnswer={onReadinessQuickAnswer}
            onApplyAnswers={onApplyReadinessAnswers}
            onPredictSparse={onPredictSparse}
            isApplying={state.status === "applying_answers"}
          />
        ) : null}
        {hasAnyInput && !predictionSignal.ready && !state.result && !readiness ? (
          <Alert>
            <AlertCircleIcon />
            <AlertTitle>More appraisal signal needed</AlertTitle>
            <AlertDescription>
              Add {predictionSignal.missingSignals.join(" and ")} before estimating. Sparse inputs collapse toward
              model defaults and produce low-confidence prices.
            </AlertDescription>
          </Alert>
        ) : null}
        {state.parseError ? (
          <Alert variant="destructive">
            <AlertCircleIcon />
            <AlertTitle>Parse failed</AlertTitle>
            <AlertDescription>{state.parseError.message}</AlertDescription>
          </Alert>
        ) : null}
        {readinessError ? (
          <Alert variant="destructive">
            <AlertCircleIcon />
            <AlertTitle>Readiness check failed</AlertTitle>
            <AlertDescription>{readinessError.message}</AlertDescription>
          </Alert>
        ) : null}
        {state.predictError ? (
          <Alert variant="destructive">
            <AlertCircleIcon />
            <AlertTitle>Prediction failed</AlertTitle>
            <AlertDescription>{state.predictError.message}</AlertDescription>
          </Alert>
        ) : null}
        <WorkflowTask state={state} />
        <div className="-mx-6 -mb-6 border-t bg-card/95 px-6 py-4 backdrop-blur lg:sticky lg:bottom-0">
          <Button
            className="w-full"
            onClick={isPredicted ? onReset : onPredict}
            disabled={!isPredicted && (!canPredict || state.status === "predicting" || assessing)}
          >
            {primaryLabel}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
