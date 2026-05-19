"use client";

import { SparklesIcon } from "lucide-react";

import { Suggestion, Suggestions } from "@/components/ai-elements/suggestion";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Field, FieldDescription, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { HouseFeatureName, HouseFieldValue } from "@/lib/housing/schema";
import type { ReadinessQuestion, ReadinessSuccessResponse } from "@/lib/readiness/types";

import { FIELD_CONFIG_BY_NAME } from "./field-config";

export type ReadinessAnswerValues = Partial<Record<HouseFeatureName, HouseFieldValue>>;

type ReadinessAssistantPanelProps = {
  readiness: ReadinessSuccessResponse;
  answers: ReadinessAnswerValues;
  onAnswerChange: (fieldName: HouseFeatureName, value: HouseFieldValue | undefined) => void;
  onQuickAnswer: (question: ReadinessQuestion, value: string) => void;
  onApplyAnswers: () => void;
  onPredictSparse: () => void;
  isApplying: boolean;
};

function hasAnsweredField(question: ReadinessQuestion, answers: ReadinessAnswerValues): boolean {
  return question.target_fields.some((fieldName) => {
    const value = answers[fieldName];
    return value !== null && value !== undefined && value !== "";
  });
}

function QuestionInput({
  fieldName,
  answers,
  onAnswerChange,
}: {
  fieldName: HouseFeatureName;
  answers: ReadinessAnswerValues;
  onAnswerChange: (fieldName: HouseFeatureName, value: HouseFieldValue | undefined) => void;
}) {
  const field = FIELD_CONFIG_BY_NAME.get(fieldName);
  if (!field) {
    return null;
  }

  const value = answers[fieldName];

  if (field.kind === "select") {
    return (
      <Field>
        <FieldLabel>{field.label}</FieldLabel>
        <Select
          value={value === undefined || value === null ? undefined : String(value)}
          onValueChange={(nextValue) => onAnswerChange(fieldName, nextValue || undefined)}
        >
          <SelectTrigger className="w-full">
            <SelectValue placeholder="Choose value" />
          </SelectTrigger>
          <SelectContent>
            <SelectGroup>
              {(field.options ?? []).map((option) => (
                <SelectItem key={option} value={option}>
                  {option}
                </SelectItem>
              ))}
            </SelectGroup>
          </SelectContent>
        </Select>
        {field.description ? <FieldDescription>{field.description}</FieldDescription> : null}
      </Field>
    );
  }

  return (
    <Field>
      <FieldLabel>{field.label}</FieldLabel>
      <Input
        type={field.kind === "number" ? "number" : "text"}
        min={field.min}
        max={field.max}
        step={field.valueType === "integer" ? 1 : "any"}
        value={value === undefined || value === null ? "" : String(value)}
        onChange={(event) => onAnswerChange(fieldName, event.target.value || undefined)}
      />
      {field.description ? <FieldDescription>{field.description}</FieldDescription> : null}
    </Field>
  );
}

export function ReadinessAssistantPanel({
  readiness,
  answers,
  onAnswerChange,
  onQuickAnswer,
  onApplyAnswers,
  onPredictSparse,
  isApplying,
}: ReadinessAssistantPanelProps) {
  const answeredCount = readiness.questions.filter((question) => hasAnsweredField(question, answers)).length;
  const canApply = answeredCount > 0 && !isApplying;

  return (
    <div className="flex flex-col gap-4 rounded-lg border bg-muted/30 p-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <SparklesIcon className="size-4 text-muted-foreground" />
            <p className="font-medium text-sm">Improve estimate</p>
          </div>
          <p className="text-muted-foreground text-xs">
            Add a few high-impact details before estimating, or continue with sparse input.
          </p>
        </div>
        <Badge variant="outline">{readiness.readiness_score}/100</Badge>
      </div>

      <Accordion type="single" collapsible defaultValue={readiness.questions[0]?.id}>
        {readiness.questions.map((question) => (
          <AccordionItem key={question.id} value={question.id}>
            <AccordionTrigger>
              <div className="flex flex-col gap-1">
                <span>{question.label}</span>
                {question.helper_text ? (
                  <span className="font-normal text-muted-foreground text-xs">{question.helper_text}</span>
                ) : null}
              </div>
            </AccordionTrigger>
            <AccordionContent className="flex flex-col gap-3">
              {question.quick_answers && question.target_fields.length === 1 ? (
                <Suggestions>
                  {question.quick_answers.map((answer) => (
                    <Suggestion key={answer} suggestion={answer} onClick={(value) => onQuickAnswer(question, value)} />
                  ))}
                </Suggestions>
              ) : null}
              <div className="grid gap-3">
                {question.target_fields.map((fieldName) => (
                  <QuestionInput
                    key={fieldName}
                    fieldName={fieldName}
                    answers={answers}
                    onAnswerChange={onAnswerChange}
                  />
                ))}
              </div>
            </AccordionContent>
          </AccordionItem>
        ))}
      </Accordion>

      <div className="grid grid-cols-1 gap-2">
        <Button onClick={onApplyAnswers} disabled={!canApply}>
          {isApplying ? "Applying..." : answeredCount > 0 ? `Apply ${answeredCount} answer${answeredCount === 1 ? "" : "s"}` : "Apply answers"}
        </Button>
        <Button variant="outline" onClick={onPredictSparse}>
          Predict with sparse input
        </Button>
      </div>
    </div>
  );
}
