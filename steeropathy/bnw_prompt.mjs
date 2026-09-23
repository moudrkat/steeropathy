// The exact brave-new-world prompt for a wish, printed as JSON {system, user}.
// One source of truth: the page's own systemSpec() and userMessage(), so the
// secondhand bench asks the model for a world the way the page does.
//   node steeropathy/bnw_prompt.mjs /path/to/brave-new-world "a funeral in the rain"
import { pathToFileURL } from "node:url";
import path from "node:path";

const [bnw, ...rest] = process.argv.slice(2);
const wish = rest.join(" ");
const world = await import(pathToFileURL(path.join(bnw, "world.js")).href);
const mind = await import(pathToFileURL(path.join(bnw, "mind.js")).href);
process.stdout.write(JSON.stringify({
  system: world.systemSpec({ wish }),
  user: mind.userMessage(wish, "spec"),
}));
