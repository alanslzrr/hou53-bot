"use client";

import type { FieldError as HookFormFieldError, UseFormReturn } from "react-hook-form";
import { Controller } from "react-hook-form";

import { Badge } from "@/components/ui/badge";
import { Field, FieldDescription, FieldError, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { HouseFeatureName } from "@/lib/housing/schema";

import type { EstimateFieldConfig } from "./field-config";
import type { HousingFormValues } from "./housing-form-schema";

const EMPTY_VALUE = "__empty__";

export type FieldSourceMetadata = {
  aiFilled: boolean;
  guessed: boolean;
  confidence?: number;
};

type FieldRendererProps = {
  field: EstimateFieldConfig;
  form: UseFormReturn<HousingFormValues>;
  source?: FieldSourceMetadata;
  onManualEdit: () => void;
};

function errorFor(
  errors: UseFormReturn<HousingFormValues>["formState"]["errors"],
  name: HouseFeatureName,
): HookFormFieldError | undefined {
  return errors[name] as HookFormFieldError | undefined;
}

function coerceNumberInput(value: unknown, integer: boolean): number | undefined {
  if (value === "" || value === null || value === undefined) {
    return undefined;
  }

  const parsed = integer ? Number.parseInt(String(value), 10) : Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}

function SelectField({ field, form, source, onManualEdit }: FieldRendererProps) {
  const error = errorFor(form.formState.errors, field.name);

  return (
    <Field data-invalid={Boolean(error)}>
      <FieldLabel htmlFor={field.name}>
        {field.label}
        <FieldBadges source={source} />
      </FieldLabel>
      <Controller
        control={form.control}
        name={field.name}
        render={({ field: controllerField }) => (
          <Select
            value={controllerField.value === undefined || controllerField.value === null ? EMPTY_VALUE : String(controllerField.value)}
            onValueChange={(value) => {
              controllerField.onChange(value === EMPTY_VALUE ? undefined : value);
              onManualEdit();
            }}
          >
            <SelectTrigger id={field.name} className="w-full" aria-invalid={Boolean(error)}>
              <SelectValue placeholder="Not specified" />
            </SelectTrigger>
            <SelectContent>
              <SelectGroup>
                <SelectItem value={EMPTY_VALUE}>Not specified</SelectItem>
                {(field.options ?? []).map((option) => (
                  <SelectItem key={option} value={option}>
                    {option}
                  </SelectItem>
                ))}
              </SelectGroup>
            </SelectContent>
          </Select>
        )}
      />
      <FieldMeta field={field} source={source} />
      <FieldError>{error?.message}</FieldError>
    </Field>
  );
}

function InputField({ field, form, source, onManualEdit }: FieldRendererProps) {
  const error = errorFor(form.formState.errors, field.name);
  const isInteger = field.valueType === "integer";
  const isNumber = field.kind === "number";

  return (
    <Field data-invalid={Boolean(error)}>
      <FieldLabel htmlFor={field.name}>
        {field.label}
        <FieldBadges source={source} />
      </FieldLabel>
      <Input
        id={field.name}
        type={isNumber ? "number" : "text"}
        min={field.min}
        max={field.max}
        step={isInteger ? 1 : "any"}
        aria-invalid={Boolean(error)}
        {...form.register(field.name, {
          setValueAs: (value) => (isNumber ? coerceNumberInput(value, isInteger) : value || undefined),
          onChange: onManualEdit,
        })}
      />
      <FieldMeta field={field} source={source} />
      <FieldError>{error?.message}</FieldError>
    </Field>
  );
}

function FieldBadges({ source }: { source?: FieldSourceMetadata }) {
  if (!source?.aiFilled && !source?.guessed) {
    return null;
  }

  return (
    <span className="flex items-center gap-1">
      {source.aiFilled ? <Badge variant="secondary">AI-filled</Badge> : null}
      {source.guessed ? <Badge variant="outline">needs review</Badge> : null}
    </span>
  );
}

function FieldMeta({ field, source }: { field: EstimateFieldConfig; source?: FieldSourceMetadata }) {
  const details = [
    field.description,
    source?.confidence !== undefined ? `${Math.round(source.confidence * 100)}% confidence` : undefined,
  ].filter(Boolean);

  if (details.length === 0) {
    return null;
  }

  return <FieldDescription>{details.join(" · ")}</FieldDescription>;
}

export function FieldRenderer(props: FieldRendererProps) {
  if (props.field.kind === "select") {
    return <SelectField {...props} />;
  }
  return <InputField {...props} />;
}
