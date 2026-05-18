"use client";

import type { UseFormReturn } from "react-hook-form";

import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { FieldGroup } from "@/components/ui/field";
import type { HouseFeatureName } from "@/lib/housing/schema";

import { FIELD_CONFIGS_BY_GROUP } from "./field-config";
import { FieldRenderer, type FieldSourceMetadata } from "./field-renderer";
import type { HousingFormValues } from "./housing-form-schema";

type HousingFormProps = {
  form: UseFormReturn<HousingFormValues>;
  aiFields: ReadonlySet<HouseFeatureName>;
  guessedFields: ReadonlySet<HouseFeatureName>;
  confidence: Partial<Record<HouseFeatureName, number>>;
  onManualEdit: () => void;
};

export function HousingForm({ form, aiFields, guessedFields, confidence, onManualEdit }: HousingFormProps) {
  return (
    <Accordion type="multiple" defaultValue={["location_lot", "building", "interior"]}>
      {FIELD_CONFIGS_BY_GROUP.map((group) => (
        <AccordionItem key={group.id} value={group.id}>
          <AccordionTrigger>
            <span>{group.label}</span>
            <span className="text-muted-foreground text-xs">{group.fields.length} fields</span>
          </AccordionTrigger>
          <AccordionContent>
            <FieldGroup className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              {group.fields.map((field) => {
                const source: FieldSourceMetadata = {
                  aiFilled: aiFields.has(field.name),
                  guessed: guessedFields.has(field.name),
                  confidence: confidence[field.name],
                };
                return (
                  <FieldRenderer
                    key={field.name}
                    field={field}
                    form={form}
                    source={source}
                    onManualEdit={onManualEdit}
                  />
                );
              })}
            </FieldGroup>
          </AccordionContent>
        </AccordionItem>
      ))}
    </Accordion>
  );
}
