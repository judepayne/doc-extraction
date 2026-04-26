import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { Type } from "typebox";
import path from "node:path";

const validationSchema = Type.Object({
  entity: Type.Union([
    Type.Literal("facility"),
    Type.Literal("deal"),
  ], { description: "Entity type to validate." }),
  json_path: Type.String({
    description: "Path to the extracted JSON file. Relative paths are resolved from the current project directory.",
  }),
  ruleset: Type.Optional(Type.Union([
    Type.Literal("facility"),
    Type.Literal("deal"),
  ], { description: "Ruleset to run. Defaults to the entity name." })),
});

type ValidateExtractionInput = {
  entity: "facility" | "deal";
  json_path: string;
  ruleset?: "facility" | "deal";
};

type RuleResult = {
  rule_id?: string;
  status?: string;
  message?: string;
  children?: RuleResult[];
};

function normalizePathArgument(inputPath: string): string {
  return inputPath.startsWith("@") ? inputPath.slice(1) : inputPath;
}

function flattenRuleResults(results: unknown): RuleResult[] {
  if (!Array.isArray(results)) return [];
  const flattened: RuleResult[] = [];
  const visit = (result: RuleResult) => {
    flattened.push(result);
    for (const child of result.children ?? []) visit(child);
  };
  for (const result of results) visit(result as RuleResult);
  return flattened;
}

function summarizeRuleResults(results: unknown): string {
  const flattened = flattenRuleResults(results);
  if (!flattened.length) return "No parsed validation rule results were returned.";

  const counts = new Map<string, number>();
  for (const result of flattened) {
    const status = result.status ?? "UNKNOWN";
    counts.set(status, (counts.get(status) ?? 0) + 1);
  }

  const summary = Array.from(counts.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([status, count]) => `${status}: ${count}`)
    .join(", ");

  const notable = flattened.filter((result) =>
    ["WARN", "FAIL", "ERROR", "NORUN"].includes(result.status ?? ""),
  );
  if (!notable.length) return `Rule summary: ${summary}`;

  return [
    `Rule summary: ${summary}`,
    ...notable.map((result) =>
      `- ${result.rule_id ?? "<unknown rule>"} ${result.status}: ${result.message || "No message."}`,
    ),
  ].join("\n");
}

function resolveDisplayCommand(cwd: string, params: ValidateExtractionInput): string {
  const args = [
    "tools/validate_extraction.py",
    "--entity",
    params.entity,
  ];
  if (params.ruleset) args.push("--ruleset", params.ruleset);
  args.push(params.json_path);
  return `cd ${cwd} && python3 ${args.map((arg) => JSON.stringify(arg)).join(" ")}`;
}

export default function (pi: ExtensionAPI) {
  pi.registerTool({
    name: "validate_extraction",
    label: "Validate Extraction",
    description: "Validate one extracted facility/deal JSON file using validation-lib and this project's local validation logic.",
    promptSnippet: "Validate a facility/deal extraction JSON file against the project-local validation rules.",
    promptGuidelines: [
      "Use validate_extraction after creating or editing facility/deal extraction JSON to check schema conformance and project validation rules.",
      "If validate_extraction returns FAIL, ERROR, or NORUN, inspect the validation messages and correct the extraction JSON before proceeding.",
    ],
    parameters: validationSchema,
    async execute(_toolCallId, params, signal, onUpdate, ctx) {
      const cwd = ctx.cwd;
      const normalizedJsonPath = normalizePathArgument(params.json_path);
      const jsonPath = path.isAbsolute(normalizedJsonPath)
        ? normalizedJsonPath
        : path.join(cwd, normalizedJsonPath);
      const ruleset = params.ruleset ?? params.entity;
      const scriptPath = path.join(cwd, "tools", "validate_extraction.py");

      onUpdate?.({
        content: [
          {
            type: "text",
            text: `Validating ${params.entity} extraction: ${params.json_path}`,
          },
        ],
      });

      const result = await pi.exec(
        "python3",
        [
          scriptPath,
          "--entity",
          params.entity,
          "--ruleset",
          ruleset,
          jsonPath,
        ],
        {
          cwd,
          signal,
          timeout: 120_000,
        },
      );

      let parsedResults: unknown = undefined;
      try {
        parsedResults = result.stdout ? JSON.parse(result.stdout) : undefined;
      } catch {
        // Keep raw stdout in details when output is not JSON.
      }

      const ok = result.code === 0;
      const resultSummary = summarizeRuleResults(parsedResults);
      const text = ok
        ? `Validation completed for ${params.entity}: ${params.json_path}\n\n${resultSummary}`
        : `Validation failed for ${params.entity}: ${params.json_path}\n\n${resultSummary}\n\n${result.stderr || result.stdout || "No output."}`;

      if (!ok) {
        throw new Error(text);
      }

      return {
        content: [{ type: "text", text }],
        details: {
          entity: params.entity,
          ruleset,
          jsonPath,
          command: resolveDisplayCommand(cwd, { ...params, ruleset }),
          exitCode: result.code,
          stdout: result.stdout,
          stderr: result.stderr,
          parsedResults,
        },
      };
    },
  });
}
