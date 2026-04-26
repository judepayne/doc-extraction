import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { Type } from "typebox";
import path from "node:path";

const extractPdfTextSchema = Type.Object({
  pdf_path: Type.String({
    description: "Path to the PDF file. Relative paths are resolved from the current project directory.",
  }),
  pages: Type.Optional(Type.String({
    description: "Optional 1-based page selection, e.g. '1-3,7'. Omit to extract all pages.",
  })),
  output_path: Type.Optional(Type.String({
    description: "Optional path to write the full extracted text. Relative paths are resolved from the current project directory.",
  })),
  max_chars: Type.Optional(Type.Number({
    description: "Maximum extracted text characters to return in the tool result. Defaults to 50000. Full text is still written to output_path when provided.",
  })),
});

type ExtractPdfTextInput = {
  pdf_path: string;
  pages?: string;
  output_path?: string;
  max_chars?: number;
};

function normalizePathArgument(inputPath: string): string {
  return inputPath.startsWith("@") ? inputPath.slice(1) : inputPath;
}

function resolvePath(cwd: string, inputPath: string): string {
  const normalizedPath = normalizePathArgument(inputPath);
  return path.isAbsolute(normalizedPath) ? normalizedPath : path.join(cwd, normalizedPath);
}

function displayPath(cwd: string, absolutePath: string): string {
  const relative = path.relative(cwd, absolutePath);
  return relative && !relative.startsWith("..") && !path.isAbsolute(relative)
    ? relative
    : absolutePath;
}

function assertInsideWorkspace(cwd: string, absolutePath: string, label: string): void {
  const relative = path.relative(cwd, absolutePath);
  if (relative.startsWith("..") || path.isAbsolute(relative)) {
    throw new Error(`${label} must be inside the current project directory: ${absolutePath}`);
  }
}

export default function (pi: ExtensionAPI) {
  pi.registerTool({
    name: "extract_pdf_text",
    label: "Extract PDF Text",
    description: "Extract readable text from a PDF file, optionally by page range, and optionally write the full text to a file.",
    promptSnippet: "Extract readable text from PDF files before doing document extraction.",
    promptGuidelines: [
      "Use extract_pdf_text when a task requires reading a PDF; do not rely on raw binary PDF content returned by read.",
      "If extract_pdf_text returns little or no text for a PDF, stop and report that the PDF may be scanned or otherwise not text-extractable instead of inventing content.",
      "When extracting structured JSON from a PDF, use extract_pdf_text before writing the JSON and cite page markers/source snippets from the extracted text where practical.",
    ],
    parameters: extractPdfTextSchema,
    async execute(_toolCallId, params: ExtractPdfTextInput, signal, onUpdate, ctx) {
      const cwd = ctx.cwd;
      const pdfPath = resolvePath(cwd, params.pdf_path);
      const outputPath = params.output_path ? resolvePath(cwd, params.output_path) : undefined;
      if (outputPath) assertInsideWorkspace(cwd, outputPath, "output_path");
      const scriptPath = path.join(cwd, "tools", "extract_pdf_text.py");
      const args = [scriptPath, pdfPath];

      if (params.pages) args.push("--pages", params.pages);
      if (outputPath) args.push("--output", outputPath);
      if (typeof params.max_chars === "number") args.push("--max-chars", String(params.max_chars));

      onUpdate?.({
        content: [
          {
            type: "text",
            text: `Extracting text from PDF: ${params.pdf_path}`,
          },
        ],
      });

      const result = await pi.exec("python3", args, {
        cwd,
        signal,
        timeout: 120_000,
      });

      let parsed: any = undefined;
      try {
        parsed = result.stdout ? JSON.parse(result.stdout) : undefined;
      } catch {
        // Return raw stdout/stderr below.
      }

      if (result.code !== 0 || !parsed) {
        throw new Error(
          `PDF text extraction failed for ${params.pdf_path}\n\n${result.stderr || result.stdout || "No output."}`,
        );
      }

      const outputNote = outputPath
        ? `\nFull extracted text written to: ${displayPath(cwd, outputPath)}`
        : "";
      const truncationNote = parsed.truncated
        ? `\nReturned text is truncated to ${parsed.returned_char_count} of ${parsed.char_count} characters. Use output_path or a narrower pages range for the full text.`
        : "";

      return {
        content: [
          {
            type: "text",
            text: `Extracted ${parsed.pages_extracted.length} page(s) from ${params.pdf_path}.${outputNote}${truncationNote}\n\n${parsed.text}`,
          },
        ],
        details: {
          pdfPath,
          outputPath,
          pageCount: parsed.page_count,
          pagesExtracted: parsed.pages_extracted,
          charCount: parsed.char_count,
          returnedCharCount: parsed.returned_char_count,
          truncated: parsed.truncated,
        },
      };
    },
  });
}
