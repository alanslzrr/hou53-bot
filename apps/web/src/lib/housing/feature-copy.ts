export type FeatureCopy = {
  label: string;
  description: string;
};

const HOUSE_FEATURE_COPY: Record<string, FeatureCopy> = {
  LotFrontage: {
    label: "Street frontage",
    description: "Linear feet of street connected to the property.",
  },
  LotArea: {
    label: "Lot area",
    description: "Total property lot size in square feet.",
  },
  MasVnrArea: {
    label: "Masonry veneer area",
    description: "Square feet of brick or stone veneer on the exterior.",
  },
  BsmtFinSF1: {
    label: "Primary finished basement area",
    description: "Finished basement square footage for the main finished area.",
  },
  BsmtFinSF2: {
    label: "Secondary finished basement area",
    description: "Finished basement square footage for a second finished area.",
  },
  BsmtUnfSF: {
    label: "Unfinished basement area",
    description: "Basement square footage that is not finished living space.",
  },
  TotalBsmtSF: {
    label: "Total basement area",
    description: "Total basement square footage, finished and unfinished.",
  },
  "1stFlrSF": {
    label: "First-floor area",
    description: "Square footage on the first floor above ground.",
  },
  "2ndFlrSF": {
    label: "Second-floor area",
    description: "Square footage on the second floor above ground.",
  },
  LowQualFinSF: {
    label: "Low-quality finished area",
    description: "Finished square footage that is lower quality than standard living area.",
  },
  GrLivArea: {
    label: "Above-grade living area",
    description: "Finished living area above ground, measured in square feet.",
  },
  BsmtFullBath: {
    label: "Basement full baths",
    description: "Number of full bathrooms located in the basement.",
  },
  BsmtHalfBath: {
    label: "Basement half baths",
    description: "Number of half bathrooms located in the basement.",
  },
  FullBath: {
    label: "Full baths",
    description: "Number of full bathrooms above ground.",
  },
  HalfBath: {
    label: "Half baths",
    description: "Number of half bathrooms above ground.",
  },
  BedroomAbvGr: {
    label: "Bedrooms",
    description: "Number of bedrooms above basement level.",
  },
  KitchenAbvGr: {
    label: "Kitchens",
    description: "Number of kitchens above basement level.",
  },
  TotRmsAbvGrd: {
    label: "Rooms above ground",
    description: "Total rooms above ground, excluding bathrooms.",
  },
  Fireplaces: {
    label: "Fireplaces",
    description: "Number of fireplaces in the home.",
  },
  GarageCars: {
    label: "Garage car capacity",
    description: "How many cars can fit in the garage.",
  },
  GarageArea: {
    label: "Garage area",
    description: "Garage size in square feet.",
  },
  WoodDeckSF: {
    label: "Wood deck area",
    description: "Wood deck square footage attached to the property.",
  },
  OpenPorchSF: {
    label: "Open porch area",
    description: "Open porch square footage.",
  },
  EnclosedPorch: {
    label: "Enclosed porch area",
    description: "Enclosed porch square footage.",
  },
  "3SsnPorch": {
    label: "Three-season porch area",
    description: "Three-season porch square footage.",
  },
  ScreenPorch: {
    label: "Screen porch area",
    description: "Screened porch square footage.",
  },
  PoolArea: {
    label: "Pool area",
    description: "Pool square footage; use 0 when there is no pool.",
  },
  MiscVal: {
    label: "Miscellaneous feature value",
    description: "Dollar value of extra property features not captured elsewhere.",
  },
  YearBuilt: {
    label: "Year built",
    description: "Original construction year of the home.",
  },
  YearRemodAdd: {
    label: "Year remodeled",
    description: "Most recent remodel year, or the build year if never remodeled.",
  },
  GarageYrBlt: {
    label: "Garage year built",
    description: "Year the garage was built, if the property has one.",
  },
  ExterQual: {
    label: "Exterior quality",
    description: "Overall quality of the exterior materials.",
  },
  ExterCond: {
    label: "Exterior condition",
    description: "Current condition of the exterior materials.",
  },
  BsmtQual: {
    label: "Basement quality",
    description: "Basement height and overall quality.",
  },
  BsmtCond: {
    label: "Basement condition",
    description: "General condition of the basement.",
  },
  HeatingQC: {
    label: "Heating quality",
    description: "Quality and condition of the heating system.",
  },
  KitchenQual: {
    label: "Kitchen quality",
    description: "Overall quality of the kitchen.",
  },
  FireplaceQu: {
    label: "Fireplace quality",
    description: "Quality of the fireplace, or not applicable if there is none.",
  },
  GarageQual: {
    label: "Garage quality",
    description: "Overall quality of the garage.",
  },
  GarageCond: {
    label: "Garage condition",
    description: "Current condition of the garage.",
  },
  PoolQC: {
    label: "Pool quality",
    description: "Overall quality of the pool, or not applicable if there is none.",
  },
  LotShape: {
    label: "Lot shape",
    description: "How regular or irregular the property lot shape is.",
  },
  LandSlope: {
    label: "Land slope",
    description: "Slope severity of the property land.",
  },
  BsmtExposure: {
    label: "Basement exposure",
    description: "Walkout or garden-level exposure of the basement walls.",
  },
  BsmtFinType1: {
    label: "Primary basement finish",
    description: "Quality of the main finished basement area.",
  },
  BsmtFinType2: {
    label: "Secondary basement finish",
    description: "Quality of the second finished basement area.",
  },
  GarageFinish: {
    label: "Garage finish",
    description: "Interior finish level of the garage.",
  },
  PavedDrive: {
    label: "Paved driveway",
    description: "Whether the driveway is paved.",
  },
  Functional: {
    label: "Home functionality",
    description: "Rating for whether the home functions normally or has layout/system deductions.",
  },
  Fence: {
    label: "Fence quality",
    description: "Quality of the fence, or not applicable when there is no fence.",
  },
  OverallQual: {
    label: "Overall quality",
    description: "Overall material and finish quality on the Ames 1-10 scale.",
  },
  OverallCond: {
    label: "Overall condition",
    description: "Overall condition of the home on the Ames 1-10 scale.",
  },
  MSZoning: {
    label: "Zoning",
    description: "General zoning classification for the property.",
  },
  Street: {
    label: "Street access",
    description: "Type of road access to the property.",
  },
  Alley: {
    label: "Alley access",
    description: "Type of alley access, or not applicable if there is none.",
  },
  LandContour: {
    label: "Land contour",
    description: "Flatness or contour of the property land.",
  },
  Utilities: {
    label: "Utilities",
    description: "Type of utilities available to the property.",
  },
  LotConfig: {
    label: "Lot configuration",
    description: "How the lot is positioned, such as inside, corner, or cul-de-sac.",
  },
  Neighborhood: {
    label: "Neighborhood",
    description: "Physical neighborhood within Ames city limits.",
  },
  Condition1: {
    label: "Primary nearby condition",
    description: "Primary proximity condition, such as road, railroad, or normal surroundings.",
  },
  Condition2: {
    label: "Secondary nearby condition",
    description: "Secondary proximity condition, if another condition applies.",
  },
  BldgType: {
    label: "Building type",
    description: "Type of dwelling, such as single-family, duplex, or townhouse.",
  },
  HouseStyle: {
    label: "House style",
    description: "Home style, such as one-story, two-story, or split-level.",
  },
  RoofStyle: {
    label: "Roof style",
    description: "Shape or style of the roof.",
  },
  RoofMatl: {
    label: "Roof material",
    description: "Primary material used for the roof.",
  },
  Exterior1st: {
    label: "Primary exterior material",
    description: "Main exterior covering material on the home.",
  },
  Exterior2nd: {
    label: "Secondary exterior material",
    description: "Secondary exterior covering material when more than one is used.",
  },
  MasVnrType: {
    label: "Masonry veneer type",
    description: "Type of masonry veneer, such as brick face, stone, or none.",
  },
  Foundation: {
    label: "Foundation",
    description: "Type of foundation under the house.",
  },
  Heating: {
    label: "Heating type",
    description: "Primary heating system type.",
  },
  CentralAir: {
    label: "Central air",
    description: "Whether the home has central air conditioning.",
  },
  Electrical: {
    label: "Electrical system",
    description: "Type of electrical system in the home.",
  },
  GarageType: {
    label: "Garage type",
    description: "Garage location or style, such as attached, detached, or none.",
  },
  MiscFeature: {
    label: "Miscellaneous feature",
    description: "Extra feature not covered elsewhere, such as a shed or second garage.",
  },
  SaleType: {
    label: "Sale type",
    description: "Type of sale transaction.",
  },
  SaleCondition: {
    label: "Sale condition",
    description: "Condition of sale, such as normal, partial, family, or abnormal.",
  },
  MSSubClass: {
    label: "Building class",
    description: "Ames dwelling class code that describes the building type and era.",
  },
  MoSold: {
    label: "Month sold",
    description: "Month when the property was sold.",
  },
  YrSold: {
    label: "Year sold",
    description: "Year when the property was sold.",
  },
};

const MODEL_FEATURE_COPY: Record<string, FeatureCopy> = {
  HouseAge: {
    label: "House age",
    description: "Age of the home at the time of sale.",
  },
  RemodAge: {
    label: "Remodel age",
    description: "Years between the last remodel and the sale.",
  },
  GarageAge: {
    label: "Garage age",
    description: "Age of the garage at the time of sale.",
  },
  TotalSF: {
    label: "Total square footage",
    description: "First-floor, second-floor, and basement area combined.",
  },
  TotalBathrooms: {
    label: "Total bathrooms",
    description: "Full baths plus half baths, including basement bathrooms.",
  },
  TotalPorchSF: {
    label: "Total porch area",
    description: "Open, enclosed, three-season, and screen porch area combined.",
  },
  AllFloorsSF: {
    label: "Above-ground floor area",
    description: "First-floor and second-floor square footage combined.",
  },
  QualArea: {
    label: "Quality-weighted living area",
    description: "Overall quality multiplied by above-grade living area.",
  },
  QualTotalSF: {
    label: "Quality-weighted total area",
    description: "Overall quality multiplied by total floor and basement area.",
  },
  HasGarage: {
    label: "Has garage",
    description: "Model flag for whether the property has a garage.",
  },
  IsRemodeled: {
    label: "Was remodeled",
    description: "Model flag for whether the remodel year differs from the build year.",
  },
  IsNewHouse: {
    label: "New at sale",
    description: "Model flag for whether the home was sold in the year it was built.",
  },
  HasPool: {
    label: "Has pool",
    description: "Model flag for whether the property has a pool.",
  },
  Has2ndFloor: {
    label: "Has second floor",
    description: "Model flag for whether the home has second-floor square footage.",
  },
  HasBsmt: {
    label: "Has basement",
    description: "Model flag for whether the home has basement area.",
  },
  HasFireplace: {
    label: "Has fireplace",
    description: "Model flag for whether the home has at least one fireplace.",
  },
  NeighborhoodPriceLog: {
    label: "Neighborhood price signal",
    description: "Historical Ames sale-price signal learned from the neighborhood.",
  },
};

function splitCamelCase(value: string): string {
  return value
    .replace(/^1st/, "1st ")
    .replace(/^2nd/, "2nd ")
    .replace(/^3Ssn/, "Three-season ")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/([A-Za-z])(\d)/g, "$1 $2")
    .replace(/\bSF\b/g, "square feet")
    .trim();
}

function sentenceCase(value: string): string {
  if (!value) {
    return value;
  }
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function cleanCategoryValue(value: string): string {
  return value
    .replace(/^'|'$/g, "")
    .replace(/_/g, " ")
    .replace(/\binfrequent sklearn\b/i, "an uncommon value");
}

function oneHotFeatureCopy(feature: string): FeatureCopy | undefined {
  const match = /^([A-Za-z][A-Za-z0-9]*)_(.+)$/.exec(feature);
  if (!match) {
    return undefined;
  }

  const [, baseFeature, rawValue] = match;
  const base = HOUSE_FEATURE_COPY[baseFeature];
  if (!base) {
    return undefined;
  }

  const value = cleanCategoryValue(rawValue);
  return {
    label: `${base.label}: ${value}`,
    description: `Whether ${base.label.toLowerCase()} is ${value}.`,
  };
}

export function getHouseFeatureCopy(feature: string): FeatureCopy {
  return HOUSE_FEATURE_COPY[feature] ?? {
    label: sentenceCase(splitCamelCase(feature)),
    description: "Ames Housing input used by the valuation model.",
  };
}

export function getModelFeatureCopy(feature: string): FeatureCopy {
  return MODEL_FEATURE_COPY[feature] ?? HOUSE_FEATURE_COPY[feature] ?? oneHotFeatureCopy(feature) ?? {
    label: sentenceCase(splitCamelCase(feature)),
    description: "Model feature used as one driver of the estimated price.",
  };
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export function humanizeExplanationText(text: string, featureNames: readonly string[]): string {
  const replacements = new Map<string, string>();

  for (const featureName of featureNames) {
    replacements.set(featureName, getModelFeatureCopy(featureName).label);
  }

  for (const featureName of Object.keys(MODEL_FEATURE_COPY)) {
    replacements.set(featureName, MODEL_FEATURE_COPY[featureName].label);
  }

  return [...replacements.entries()]
    .sort(([left], [right]) => right.length - left.length)
    .reduce((current, [rawName, label]) => {
      return current.replace(new RegExp(`\\b${escapeRegExp(rawName)}\\b`, "g"), label);
    }, text);
}
