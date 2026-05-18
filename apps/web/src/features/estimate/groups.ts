import type { HouseFeatureName } from "@/lib/housing/schema";

export type FieldGroupId =
  | "location_lot"
  | "building"
  | "exterior_masonry"
  | "basement"
  | "systems"
  | "interior"
  | "baths"
  | "fireplace_garage"
  | "outdoor"
  | "sale_metadata";

export type FieldGroupConfig = {
  id: FieldGroupId;
  label: string;
  fields: readonly HouseFeatureName[];
};

export const FIELD_GROUPS: readonly FieldGroupConfig[] = [
  {
    id: "location_lot",
    label: "Location & lot",
    fields: [
      "MSSubClass",
      "MSZoning",
      "LotFrontage",
      "LotArea",
      "Street",
      "Alley",
      "LotShape",
      "LandContour",
      "Utilities",
      "LotConfig",
      "LandSlope",
      "Neighborhood",
      "Condition1",
      "Condition2",
    ],
  },
  {
    id: "building",
    label: "Building",
    fields: [
      "BldgType",
      "HouseStyle",
      "OverallQual",
      "OverallCond",
      "YearBuilt",
      "YearRemodAdd",
      "RoofStyle",
      "RoofMatl",
      "Exterior1st",
      "Exterior2nd",
    ],
  },
  {
    id: "exterior_masonry",
    label: "Exterior & masonry",
    fields: ["MasVnrType", "MasVnrArea", "ExterQual", "ExterCond", "Foundation"],
  },
  {
    id: "basement",
    label: "Basement",
    fields: [
      "BsmtQual",
      "BsmtCond",
      "BsmtExposure",
      "BsmtFinType1",
      "BsmtFinSF1",
      "BsmtFinType2",
      "BsmtFinSF2",
      "BsmtUnfSF",
      "TotalBsmtSF",
    ],
  },
  {
    id: "systems",
    label: "Systems",
    fields: ["Heating", "HeatingQC", "CentralAir", "Electrical"],
  },
  {
    id: "interior",
    label: "Interior",
    fields: [
      "1stFlrSF",
      "2ndFlrSF",
      "LowQualFinSF",
      "GrLivArea",
      "BedroomAbvGr",
      "KitchenAbvGr",
      "KitchenQual",
      "TotRmsAbvGrd",
      "Functional",
    ],
  },
  {
    id: "baths",
    label: "Baths",
    fields: ["BsmtFullBath", "BsmtHalfBath", "FullBath", "HalfBath"],
  },
  {
    id: "fireplace_garage",
    label: "Fireplace & garage",
    fields: [
      "Fireplaces",
      "FireplaceQu",
      "GarageType",
      "GarageYrBlt",
      "GarageFinish",
      "GarageCars",
      "GarageArea",
      "GarageQual",
      "GarageCond",
    ],
  },
  {
    id: "outdoor",
    label: "Outdoor",
    fields: [
      "PavedDrive",
      "WoodDeckSF",
      "OpenPorchSF",
      "EnclosedPorch",
      "3SsnPorch",
      "ScreenPorch",
      "PoolArea",
      "PoolQC",
      "Fence",
      "MiscFeature",
      "MiscVal",
    ],
  },
  {
    id: "sale_metadata",
    label: "Sale metadata",
    fields: ["MoSold", "YrSold", "SaleType", "SaleCondition"],
  },
];

export const FIELD_GROUP_BY_NAME = new Map<HouseFeatureName, FieldGroupId>(
  FIELD_GROUPS.flatMap((group) => group.fields.map((field) => [field, group.id] as const)),
);
