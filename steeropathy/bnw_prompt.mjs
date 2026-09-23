// The exact brave-new-world prompt for a wish, printed as JSON {system, user}.
// One source of truth: the page's own systemSpec() and userMessage(), so the
// secondhand bench asks the model for a world the way the page does.
//   node steeropathy/bnw_prompt.mjs /path/to/brave-new-world "<wish>" ["<example wish>"]
// The page tunes the worked example in the system prompt to the wish; the
// optional third argument builds the example for ANOTHER wish instead, so
// every mind in a bench can share one generic example (prompt-structural
// features are surface form, Wenzel 2026 — keep them identical on both sides).
import { pathToFileURL } from "node:url";
import path from "node:path";

const [bnw, wish, exampleWish] = process.argv.slice(2);
const world = await import(pathToFileURL(path.join(bnw, "world.js")).href);
const mind = await import(pathToFileURL(path.join(bnw, "mind.js")).href);
process.stdout.write(JSON.stringify({
  system: world.systemSpec({ wish: exampleWish ?? wish }),
  user: mind.userMessage(wish, "spec"),
}));
