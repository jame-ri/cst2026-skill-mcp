import { InputError, validateArguments } from "../shared/runtime.js";
import { assertPortable } from "../shared/data.js";
import { relativePath } from "../shared/paths.js";

const allowed = new Set(["type", "description", "title", "properties", "required", "additionalProperties",
  "items", "minItems", "maxItems", "minLength", "maxLength", "minimum", "maximum", "enum", "default", "pattern"]);
const types = new Set(["object", "array", "string", "number", "integer", "boolean", "null"]);
const reserved = new Set(["__proto__", "prototype", "constructor"]);
const object = value => value !== null && typeof value === "object" && !Array.isArray(value);
const fail = message => { throw new InputError(message); };

export function checkSchema(schema, depth = 0) {
  if (!object(schema) || depth > 16) fail("API input_schema must be a bounded schema object.");
  for (const key of Object.keys(schema)) if (!allowed.has(key)) fail("Unsupported schema keyword: " + key);
  if (!types.has(schema.type)) fail("Each schema node requires one supported type; unions and references are not supported.");
  for (const key of ["description", "title"]) if (schema[key] !== undefined && typeof schema[key] !== "string") fail(key + " must be text.");
  for (const key of ["minItems", "maxItems", "minLength", "maxLength"]) {
    if (schema[key] !== undefined && (!Number.isInteger(schema[key]) || schema[key] < 0)) fail(key + " must be a nonnegative integer.");
  }
  for (const key of ["minimum", "maximum"]) if (schema[key] !== undefined && !Number.isFinite(schema[key])) fail(key + " must be finite.");
  for (const [minimum, maximum] of [["minItems", "maxItems"], ["minLength", "maxLength"], ["minimum", "maximum"]]) {
    if (schema[minimum] !== undefined && schema[maximum] !== undefined && schema[minimum] > schema[maximum]) fail("Schema minimum exceeds maximum.");
  }
  if (schema.enum !== undefined && (!Array.isArray(schema.enum) || !schema.enum.length || schema.enum.length > 100)) fail("enum needs 1-100 values.");
  if (schema.pattern !== undefined) {
    if (schema.type !== "string" || typeof schema.pattern !== "string" || schema.pattern.length > 256) fail("pattern requires a bounded string schema.");
    try { new RegExp(schema.pattern); } catch { fail("Invalid schema pattern."); }
  }
  if (schema.type === "object") {
    if (!object(schema.properties) || schema.additionalProperties !== false) fail("Object schemas require properties and additionalProperties=false.");
    const keys = Object.keys(schema.properties);
    if (keys.length > 100 || keys.some(key => reserved.has(key))) fail("Too many or reserved API property names.");
    if (schema.required !== undefined && (!Array.isArray(schema.required) ||
        new Set(schema.required).size !== schema.required.length || schema.required.some(key => typeof key !== "string" || !keys.includes(key)))) fail("required must list distinct declared property names.");
    Object.values(schema.properties).forEach(child => checkSchema(child, depth + 1));
  } else if (["properties", "required", "additionalProperties"].some(key => key in schema)) fail("Object keywords require type=object.");
  if (schema.type === "array") {
    if (!schema.items) fail("Array schemas require items.");
    checkSchema(schema.items, depth + 1);
    if ((schema.maxItems ?? 1000) > 1000) fail("API arrays are limited to 1000 items.");
  } else if (["items", "minItems", "maxItems"].some(key => key in schema)) fail("Array keywords require type=array.");
  if (["minLength", "maxLength", "pattern"].some(key => key in schema) && schema.type !== "string") fail("String keywords require type=string.");
  if (["minimum", "maximum"].some(key => key in schema) && !["number", "integer"].includes(schema.type)) fail("Numeric bounds require a numeric type.");
  if (schema.default !== undefined) validateArguments(schema.default, schema);
}

export function validateInput(value, schema) {
  validateArguments(value, schema);
  // Enforce explicit lower bounds even for clients that treat them as annotations.
  const lowerBounds = (item, node) => {
    if (typeof item === "string" && item.length < (node.minLength ?? 0)) fail("API string is shorter than minLength.");
    if (Array.isArray(item)) {
      if (item.length < (node.minItems ?? 0)) fail("API array is shorter than minItems.");
      item.forEach(child => lowerBounds(child, node.items));
    } else if (object(item) && node.properties) {
      for (const [key, child] of Object.entries(item)) if (node.properties[key]) lowerBounds(child, node.properties[key]);
    }
  };
  lowerBounds(value, schema);
  assertPortable(value, "API arguments");
}

export function candidateMetadata(value) {
  const fields = new Set(["id", "version", "description", "input_schema", "effect", "cst_version",
    "implementation", "entrypoint", "verifier", "references", "tags"]);
  if (!object(value) || Object.keys(value).some(key => !fields.has(key))) fail("Unknown or invalid candidate metadata.");
  if (!/^user\.[a-z][a-z0-9_.]{1,79}$/.test(value.id ?? "")) fail("Candidate IDs must use the user. namespace.");
  if (!/^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/.test(value.version ?? "")) fail("version must be major.minor.patch.");
  if (typeof value.description !== "string" || !value.description.trim() || value.description.length > 4000) fail("Provide a description of up to 4000 characters.");
  if (!["read", "modify", "solve"].includes(value.effect)) fail("effect must be read, modify or solve.");
  if (!/^20\d{2}$/.test(value.cst_version ?? "")) fail("cst_version must identify the supported CST year.");
  for (const key of ["entrypoint", "verifier"]) if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(value[key] ?? "")) fail(key + " must name a top-level Python function.");
  if (value.entrypoint === value.verifier) fail("Execution and verification must be separate functions.");
  const implementation = relativePath(value.implementation);
  if (!implementation.endsWith(".py")) fail("implementation must be a repository-relative Python file.");
  if (!Array.isArray(value.references) || !value.references.length || value.references.length > 24) fail("Provide 1-24 repository-relative source references.");
  const references = value.references.map(relativePath);
  const tags = value.tags ?? [];
  if (!Array.isArray(tags) || tags.length > 24 || tags.some(tag => typeof tag !== "string" || !tag.trim() || tag.length > 80)) fail("tags must contain bounded strings.");
  checkSchema(value.input_schema);
  if (value.input_schema.type !== "object") fail("The root input_schema must be an object.");
  assertPortable({ description: value.description, tags });
  return { ...value, implementation, references, tags };
}

const id = { type: "string", pattern: "^[a-f0-9-]{36}$" };
export function extensionSchema(metadata) {
  return { type: "object", properties: {
    session_id: id, project_id: id, parameters: metadata.input_schema,
    execute: { type: "boolean", default: false },
    allow_extension_execution: { type: "boolean", default: false },
    allow_solve: { type: "boolean", default: false },
    operation_id: id,
    timeout_sec: { type: "integer", minimum: 5, maximum: 600, default: 120 }
  }, required: ["session_id", "project_id", "parameters"], additionalProperties: false };
}
