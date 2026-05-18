import type { HouseFeatureName, HouseFieldValue } from "@/lib/housing/schema";

export type DirtyHouseFields = Partial<Record<HouseFeatureName, boolean>>;

export function staleParsedFieldNamesToClear({
  previousAiFields,
  previousGuessedFields,
  nextFields,
  dirtyFields,
}: {
  previousAiFields: ReadonlySet<HouseFeatureName>;
  previousGuessedFields: ReadonlySet<HouseFeatureName>;
  nextFields: Partial<Record<HouseFeatureName, HouseFieldValue>>;
  dirtyFields: DirtyHouseFields;
}): HouseFeatureName[] {
  const nextFieldNames = new Set(Object.keys(nextFields) as HouseFeatureName[]);
  const previousModelFields = new Set<HouseFeatureName>([
    ...previousAiFields,
    ...previousGuessedFields,
  ]);

  return [...previousModelFields].filter((fieldName) => {
    return !nextFieldNames.has(fieldName) && !dirtyFields[fieldName];
  });
}
