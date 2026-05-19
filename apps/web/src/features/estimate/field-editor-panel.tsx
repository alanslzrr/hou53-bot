"use client";

import type { UseFormReturn } from "react-hook-form";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { FieldGroup } from "@/components/ui/field";
import type { HouseFeatureName } from "@/lib/housing/schema";

import { ESTIMATE_FIELD_CONFIGS, FIELD_CONFIG_BY_NAME } from "./field-config";
import { FieldRenderer, type FieldSourceMetadata } from "./field-renderer";
import { HousingForm } from "./housing-form";
import type { HousingFormValues } from "./housing-form-schema";

const HIGH_SIGNAL_FIELDS = [
  "GrLivArea",
  "OverallQual",
  "YearBuilt",
  "Neighborhood",
  "TotalBsmtSF",
  "GarageCars",
  "FullBath",
] as const satisfies readonly HouseFeatureName[];

type FieldEditorPanelProps = {
  form: UseFormReturn<HousingFormValues>;
  aiFields: ReadonlySet<HouseFeatureName>;
  guessedFields: ReadonlySet<HouseFeatureName>;
  confidence: Partial<Record<HouseFeatureName, number>>;
  onManualEdit: () => void;
};

function fieldSource(
  fieldName: HouseFeatureName,
  aiFields: ReadonlySet<HouseFeatureName>,
  guessedFields: ReadonlySet<HouseFeatureName>,
  confidence: Partial<Record<HouseFeatureName, number>>,
): FieldSourceMetadata {
  return {
    aiFilled: aiFields.has(fieldName),
    guessed: guessedFields.has(fieldName),
    confidence: confidence[fieldName],
  };
}

function promotedFieldNames(
  aiFields: ReadonlySet<HouseFeatureName>,
  guessedFields: ReadonlySet<HouseFeatureName>,
): HouseFeatureName[] {
  const promoted = new Set<HouseFeatureName>();
  const ordered: HouseFeatureName[] = [];

  for (const fieldName of HIGH_SIGNAL_FIELDS) {
    if (FIELD_CONFIG_BY_NAME.has(fieldName)) {
      promoted.add(fieldName);
      ordered.push(fieldName);
    }
  }

  for (const field of ESTIMATE_FIELD_CONFIGS) {
    if (!promoted.has(field.name) && (aiFields.has(field.name) || guessedFields.has(field.name))) {
      promoted.add(field.name);
      ordered.push(field.name);
    }
  }

  return ordered;
}

export function FieldEditorPanel({
  form,
  aiFields,
  guessedFields,
  confidence,
  onManualEdit,
}: FieldEditorPanelProps) {
  const promotedFields = promotedFieldNames(aiFields, guessedFields);

  return (
    <section className="flex min-h-0 flex-col gap-5 lg:overflow-y-auto lg:py-5 lg:pl-2">
      <Card size="sm" className="shrink-0">
        <CardHeader>
          <CardTitle>Guided review</CardTitle>
          <CardDescription>High-signal and AI-filled fields</CardDescription>
        </CardHeader>
        <CardContent>
          <FieldGroup className="grid grid-cols-1 gap-4">
            {promotedFields.map((fieldName) => {
              const field = FIELD_CONFIG_BY_NAME.get(fieldName);
              if (!field) {
                return null;
              }

              return (
                <FieldRenderer
                  key={field.name}
                  field={field}
                  form={form}
                  source={fieldSource(field.name, aiFields, guessedFields, confidence)}
                  onManualEdit={onManualEdit}
                />
              );
            })}
          </FieldGroup>
        </CardContent>
      </Card>

      <div className="flex flex-col gap-3">
        <div className="flex items-end justify-between gap-3 px-1">
          <div>
            <h2 className="font-heading text-base font-medium">Full field editor</h2>
            <p className="text-muted-foreground text-sm">All remaining Ames features</p>
          </div>
        </div>
        <HousingForm
          form={form}
          aiFields={aiFields}
          guessedFields={guessedFields}
          confidence={confidence}
          onManualEdit={onManualEdit}
          promotedFields={promotedFields}
          layout="rail"
        />
      </div>
    </section>
  );
}
