import { z } from "zod";

import { houseFieldsSchema } from "@/lib/housing/schema";

export const housingFormSchema = houseFieldsSchema;
export type HousingFormValues = z.infer<typeof housingFormSchema>;
