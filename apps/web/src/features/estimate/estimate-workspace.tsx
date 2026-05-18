"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import type { ChatStatus } from "ai";
import { nanoid } from "nanoid";
import { useMemo, useReducer, useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";

import {
  PromptInput,
  PromptInputBody,
  PromptInputFooter,
  type PromptInputMessage,
  PromptInputProvider,
  PromptInputSubmit,
  PromptInputTextarea,
  PromptInputTools,
  usePromptInputController,
} from "@/components/ai-elements/prompt-input";
import { Suggestion, Suggestions } from "@/components/ai-elements/suggestion";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { HouseFeatureName, HouseFieldValue, HouseFields } from "@/lib/housing/schema";
import type { ParseResponse } from "@/lib/nlp/types";
import type { PredictionInputSource, PredictionParseMetadata } from "@/server/db/schema";
import type { PredictRouteResponse } from "@/server/predict/types";

import { estimateReducer, initialEstimateState } from "./estimate-state";
import { HousingForm } from "./housing-form";
import { housingFormSchema, type HousingFormValues } from "./housing-form-schema";
import { staleParsedFieldNamesToClear } from "./parse-field-application";
import { ResultPanel } from "./result-panel";

const PROMPT_SUGGESTIONS = [
  "A 2-story house in North Ames with 1,850 sqft, 3 bedrooms, 2 full baths, built in 1998 and a 2-car attached garage.",
  "A newer Stone Brook home with excellent overall quality, 2,400 sqft living area, finished garage and central air.",
  "An older Old Town property from 1920, average condition, 1,250 sqft, no garage, small lot and unfinished basement.",
];

function pruneFields(values: HousingFormValues): HouseFields {
  const fields: HouseFields = {};
  for (const [key, value] of Object.entries(values)) {
    if (value !== null && value !== undefined && value !== "") {
      fields[key as HouseFeatureName] = value as HouseFieldValue;
    }
  }
  return fields;
}

function hasMeaningfulFields(values: Partial<HousingFormValues> | undefined): boolean {
  return Object.values(values ?? {}).some((value) => value !== null && value !== undefined && value !== "");
}

function compactConfidence(confidence: Partial<Record<HouseFeatureName, number>>): Record<string, number> {
  return Object.fromEntries(
    Object.entries(confidence).filter((entry): entry is [string, number] => entry[1] !== undefined),
  );
}

function PromptComposer({
  onSubmit,
  status,
}: {
  onSubmit: (description: string) => Promise<void>;
  status: ChatStatus;
}) {
  const controller = usePromptInputController();

  async function handleSubmit(message: PromptInputMessage) {
    const text = message.text.trim();
    if (!text) {
      return;
    }
    await onSubmit(text);
    controller.textInput.clear();
  }

  return (
    <div className="flex flex-col gap-3">
      <PromptInput onSubmit={(message) => void handleSubmit(message)}>
        <PromptInputBody>
          <PromptInputTextarea placeholder="Describe the house: location, year, area, rooms, quality, garage..." />
        </PromptInputBody>
        <PromptInputFooter>
          <PromptInputTools>
            <Badge variant="outline">single-shot parse</Badge>
          </PromptInputTools>
          <PromptInputSubmit status={status} />
        </PromptInputFooter>
      </PromptInput>
      <Suggestions>
        {PROMPT_SUGGESTIONS.map((suggestion) => (
          <Suggestion
            key={suggestion}
            suggestion={suggestion}
            onClick={(value) => controller.textInput.setInput(value)}
          />
        ))}
      </Suggestions>
    </div>
  );
}

export function EstimateWorkspace() {
  const [state, dispatch] = useReducer(estimateReducer, initialEstimateState);
  const [aiFields, setAiFields] = useState<ReadonlySet<HouseFeatureName>>(new Set());
  const [guessedFields, setGuessedFields] = useState<ReadonlySet<HouseFeatureName>>(new Set());
  const [confidence, setConfidence] = useState<Partial<Record<HouseFeatureName, number>>>({});
  const [missingFields, setMissingFields] = useState<HouseFeatureName[]>([]);
  const [parseMetadata, setParseMetadata] = useState<PredictionParseMetadata | undefined>();
  const [inputSource, setInputSource] = useState<PredictionInputSource>("manual");

  const form = useForm<HousingFormValues>({
    resolver: zodResolver(housingFormSchema),
    mode: "onChange",
    defaultValues: {},
  });
  const watchedValues = useWatch({ control: form.control });

  const filledCount = useMemo(() => Object.keys(pruneFields(watchedValues)).length, [watchedValues]);
  const canPredict = hasMeaningfulFields(watchedValues) && state.status !== "parsing" && state.status !== "predicting";

  function patchParsedFields(fields: Partial<Record<HouseFeatureName, HouseFieldValue>>) {
    const dirtyFields = form.formState.dirtyFields as Partial<Record<HouseFeatureName, boolean>>;

    for (const fieldName of staleParsedFieldNamesToClear({
      previousAiFields: aiFields,
      previousGuessedFields: guessedFields,
      nextFields: fields,
      dirtyFields,
    })) {
      form.setValue(fieldName, undefined, {
        shouldDirty: false,
        shouldTouch: false,
        shouldValidate: true,
      });
      form.clearErrors(fieldName);
    }

    for (const [name, value] of Object.entries(fields) as [HouseFeatureName, HouseFieldValue][]) {
      const currentValue = form.getValues(name);
      const isEmpty = currentValue === null || currentValue === undefined || currentValue === "";
      if (!dirtyFields[name] || isEmpty) {
        form.setValue(name, value, {
          shouldDirty: false,
          shouldTouch: false,
          shouldValidate: true,
        });
      }
    }
  }

  async function handleParse(description: string) {
    dispatch({ type: "parse_start" });

    const response = await fetch("/api/parse", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ description }),
    });
    const payload = (await response.json()) as ParseResponse;

    if (payload.ok) {
      patchParsedFields(payload.parsed_fields);
      const parsedNames = Object.keys(payload.parsed_fields) as HouseFeatureName[];
      setAiFields(new Set(parsedNames));
      setGuessedFields(new Set(payload.guessed_fields));
      setConfidence(payload.field_confidence);
      setMissingFields(payload.missing_fields);
      setParseMetadata({
        parse_request_id: payload.request_id,
        model: payload.model,
        guessed_fields: payload.guessed_fields,
        missing_fields: payload.missing_fields,
        field_confidence: compactConfidence(payload.field_confidence),
        clarification_questions: payload.clarification_questions,
      });
      setInputSource("nlp");
      dispatch({
        type: "parse_success",
        extractedCount: parsedNames.length,
        missingCount: payload.missing_fields.length,
      });
      return;
    }

    patchParsedFields(payload.partial_fields);
    dispatch({ type: "parse_error", error: payload.error });
  }

  function handleManualEdit() {
    if (aiFields.size > 0) {
      setInputSource("mixed");
    } else {
      setInputSource("manual");
    }
    dispatch({ type: "edit" });
  }

  const submitPrediction = form.handleSubmit(async (values) => {
    dispatch({ type: "predict_start" });
    const response = await fetch("/api/predict", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        fields: pruneFields(values),
        input_source: inputSource,
        parse_metadata: parseMetadata,
        idempotency_key: nanoid(),
      }),
    });
    const payload = (await response.json()) as PredictRouteResponse;

    if (payload.ok) {
      dispatch({ type: "predict_success", result: payload });
      if (payload.warning) {
        toast.warning(payload.warning);
      }
      return;
    }

    dispatch({ type: "predict_error", error: payload.error });
  });

  return (
    <main className="mx-auto grid max-w-7xl grid-cols-1 gap-5 px-4 py-5 lg:grid-cols-[minmax(0,1fr)_420px]">
      <section className="flex flex-col gap-5">
        <Card>
          <CardHeader>
            <CardTitle>New estimate</CardTitle>
            <CardDescription>Describe a house, review extracted fields, then run the model-backed valuation.</CardDescription>
          </CardHeader>
          <CardContent>
            <PromptInputProvider>
              <PromptComposer
                status={state.status === "parsing" ? "submitted" : state.status === "parse_error" ? "error" : "ready"}
                onSubmit={handleParse}
              />
            </PromptInputProvider>
          </CardContent>
        </Card>
        <HousingForm
          form={form}
          aiFields={aiFields}
          guessedFields={guessedFields}
          confidence={confidence}
          onManualEdit={handleManualEdit}
        />
      </section>
      <aside>
        <ResultPanel
          state={state}
          filledCount={filledCount}
          aiFilledCount={aiFields.size}
          missingCount={missingFields.length}
          canPredict={canPredict}
          onPredict={() => void submitPrediction()}
        />
      </aside>
    </main>
  );
}
