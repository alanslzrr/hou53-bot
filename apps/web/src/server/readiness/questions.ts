import { openai, type OpenAILanguageModelChatOptions } from "@ai-sdk/openai";
import { generateText, Output } from "ai";
import { z } from "zod";

import {
  houseFeatureNameSchema,
  type HouseFeatureName,
  type HouseFields,
} from "@/lib/housing/schema";
import {
  MAX_READINESS_QUESTIONS,
  type ReadinessAssessment,
  type ReadinessQuestion,
} from "@/lib/readiness/types";
import type { PredictionParseMetadata } from "@/server/db/schema";

const LOW_CONFIDENCE_THRESHOLD = 0.65;

const QUESTION_CANDIDATES: readonly ReadinessQuestion[] = [
  {
    id: "q_gr_liv_area",
    label: "What is the approximate above-grade living area?",
    helper_text: "A rough square-foot estimate is enough.",
    target_fields: ["GrLivArea"],
    priority: 1,
    quick_answers: ["1200", "1800", "2400"],
  },
  {
    id: "q_overall_qual",
    label: "How would you rate the overall quality?",
    helper_text: "Use the Ames 1-10 quality scale.",
    target_fields: ["OverallQual"],
    priority: 2,
    quick_answers: ["5 average", "7 good", "9 excellent"],
  },
  {
    id: "q_year_built",
    label: "About what year was the house built?",
    helper_text: "Use the original build year if known.",
    target_fields: ["YearBuilt"],
    priority: 3,
    quick_answers: ["1950", "1995", "2010"],
  },
  {
    id: "q_neighborhood",
    label: "Which Ames neighborhood is it closest to?",
    helper_text: "Pick the closest known Ames neighborhood if exact location is unknown.",
    target_fields: ["Neighborhood"],
    priority: 4,
    quick_answers: ["NAmes", "CollgCr", "OldTown"],
  },
  {
    id: "q_total_bsmt_sf",
    label: "What is the approximate basement square footage?",
    helper_text: "Use 0 if the home has no basement.",
    target_fields: ["TotalBsmtSF"],
    priority: 5,
    quick_answers: ["0", "800", "1200"],
  },
  {
    id: "q_garage_cars",
    label: "How many cars fit in the garage?",
    helper_text: "Use 0 if there is no garage.",
    target_fields: ["GarageCars"],
    priority: 6,
    quick_answers: ["0", "1", "2"],
  },
  {
    id: "q_garage_area",
    label: "What is the approximate garage area?",
    helper_text: "Use 0 if there is no garage.",
    target_fields: ["GarageArea"],
    priority: 7,
    quick_answers: ["0", "280", "480"],
  },
  {
    id: "q_full_bath",
    label: "How many full bathrooms does the house have?",
    helper_text: "Count above-grade full baths.",
    target_fields: ["FullBath"],
    priority: 8,
    quick_answers: ["1", "2", "3"],
  },
];

const enhancedQuestionSchema = z.object({
  questions: z
    .array(
      z.object({
        id: z.string().min(1),
        label: z.string().min(8).max(140),
        helper_text: z.string().min(1).max(180).optional(),
        target_fields: z.array(houseFeatureNameSchema).max(3).optional(),
      }),
    )
    .max(MAX_READINESS_QUESTIONS),
});

type BuildReadinessQuestionsInput = {
  fields: HouseFields;
  assessment: ReadinessAssessment;
  parseMetadata?: PredictionParseMetadata;
  enhanceWithLlm?: boolean;
};

function hasConcreteValue(value: unknown): boolean {
  return value !== null && value !== undefined && value !== "";
}

function targetNeedsQuestion(
  field: HouseFeatureName,
  fields: HouseFields,
  parseMetadata?: PredictionParseMetadata,
): boolean {
  const isMissing = !hasConcreteValue(fields[field]);
  const isGuessed = parseMetadata?.guessed_fields?.includes(field) ?? false;
  const confidence = parseMetadata?.field_confidence?.[field];
  const isLowConfidence = confidence !== undefined && confidence < LOW_CONFIDENCE_THRESHOLD;

  return isMissing || isGuessed || isLowConfidence;
}

function shouldAskQuestion(
  question: ReadinessQuestion,
  fields: HouseFields,
  parseMetadata?: PredictionParseMetadata,
): boolean {
  return question.target_fields.some((field) => targetNeedsQuestion(field, fields, parseMetadata));
}

export function buildRuleBasedReadinessQuestions({
  fields,
  assessment,
  parseMetadata,
}: BuildReadinessQuestionsInput): ReadinessQuestion[] {
  if (assessment.level === "strong") {
    return [];
  }

  return QUESTION_CANDIDATES.filter((question) => shouldAskQuestion(question, fields, parseMetadata))
    .sort((left, right) => left.priority - right.priority)
    .slice(0, MAX_READINESS_QUESTIONS);
}

function shouldUseLlmEnhancement(enabled?: boolean): boolean {
  if (enabled === false) {
    return false;
  }
  if (process.env.HOU53_READINESS_LLM_ENABLED === "false") {
    return false;
  }
  return Boolean(process.env.OPENAI_API_KEY);
}

function readinessModel(): string {
  return process.env.HOU53_NLP_MODEL || "gpt-5.4-mini";
}

function mergeEnhancements(
  questions: ReadinessQuestion[],
  enhanced: z.infer<typeof enhancedQuestionSchema>,
): ReadinessQuestion[] {
  const byId = new Map(enhanced.questions.map((question) => [question.id, question]));

  return questions.map((question) => {
    const enhancement = byId.get(question.id);
    if (!enhancement) {
      return question;
    }

    return {
      ...question,
      label: enhancement.label,
      helper_text: enhancement.helper_text ?? question.helper_text,
    };
  });
}

async function enhanceQuestionsWithLlm(
  questions: ReadinessQuestion[],
  assessment: ReadinessAssessment,
): Promise<ReadinessQuestion[]> {
  try {
    const { output } = await generateText({
      model: openai.chat(readinessModel()),
      system: [
        "You improve short follow-up questions for a house appraisal form.",
        "Do not predict price. Do not explain model behavior. Do not add new fields.",
        "Keep questions concise, practical, and easy to answer.",
        "Preserve each question id. Return at most the provided questions.",
      ].join("\n"),
      prompt: JSON.stringify({
        readiness_score: assessment.readiness_score,
        level: assessment.level,
        missing_signal_groups: assessment.missing_signal_groups,
        questions,
      }),
      output: Output.object({
        schema: enhancedQuestionSchema,
        name: "readiness_questions",
        description: "Improved appraisal follow-up questions using the provided question ids.",
      }),
      maxRetries: 0,
      maxOutputTokens: 1_000,
      providerOptions: {
        openai: {
          store: false,
          strictJsonSchema: false,
        } satisfies OpenAILanguageModelChatOptions,
      },
      timeout: { totalMs: 8_000 },
    });

    return mergeEnhancements(questions, output);
  } catch {
    return questions;
  }
}

export async function buildReadinessQuestions(input: BuildReadinessQuestionsInput): Promise<ReadinessQuestion[]> {
  const questions = buildRuleBasedReadinessQuestions(input);
  if (questions.length === 0 || !shouldUseLlmEnhancement(input.enhanceWithLlm)) {
    return questions;
  }

  return enhanceQuestionsWithLlm(questions, input.assessment);
}
