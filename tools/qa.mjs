// Look at the handbooks the way readers will: render them in Chrome, report errors and
// overflow, screenshot figures and panels, and print the PDF edition.
//
//   node tools/qa.mjs check <book.html...>         console errors, horizontal overflow (desktop + phone)
//   node tools/qa.mjs figs <book.html> [ids...]    screenshot figures (light + dark) into qa/
//   node tools/qa.mjs el <book.html> <selector> [name] [--dark] [--width=N]   screenshot one element
//   node tools/qa.mjs pdf <book.html...>           write pdf/<name>.pdf
import puppeteer from "puppeteer-core";
import { mkdirSync } from "node:fs";
import { resolve, basename, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const [cmd, ...args] = process.argv.slice(2);
const flags = Object.fromEntries(args.filter(a => a.startsWith("--")).map(a => { const [k, v] = a.slice(2).split("="); return [k, v ?? true]; }));
const pos = args.filter(a => !a.startsWith("--"));

const browser = await puppeteer.launch({
  executablePath: "/usr/bin/google-chrome",
  headless: true,
  args: ["--no-sandbox", "--font-render-hinting=none"],
});

async function open(file, { width = 1280, height = 900, dark = false, print = false } = {}) {
  const page = await browser.newPage();
  const errors = [];
  page.on("console", m => { if (m.type() === "error") errors.push(m.text()); });
  page.on("pageerror", e => errors.push(String(e)));
  page.on("requestfailed", r => errors.push("request failed: " + r.url()));
  await page.setViewport({ width, height, deviceScaleFactor: 1.5 });
  await page.emulateMediaFeatures([{ name: "prefers-color-scheme", value: dark ? "dark" : "light" }]);
  if (print) await page.emulateMediaType("print");
  const url = "file://" + resolve(ROOT, file) + (print ? "?print=1" : "");
  await page.goto(url, { waitUntil: "networkidle0", timeout: 120000 });
  await page.evaluate(() => document.fonts.ready);
  return { page, errors };
}

if (cmd === "check") {
  for (const file of pos) {
    for (const [label, width, height] of [["desktop", 1280, 900], ["tablet", 820, 1100], ["phone", 390, 844]]) {
      const { page, errors } = await open(file, { width, height });
      const res = await page.evaluate(() => {
        const doc = document.documentElement;
        const wide = [];
        if (doc.scrollWidth > doc.clientWidth + 1) {
          document.querySelectorAll("main *").forEach(el => {
            const r = el.getBoundingClientRect();
            if (r.right > doc.clientWidth + 1 && !el.closest(".fig-scroll, .table-wrap, pre")) wide.push(el.tagName + "." + el.className + " " + Math.round(r.right));
          });
        }
        const fonts = [...document.fonts].filter(f => f.status === "loaded").map(f => f.family);
        return { scrollWidth: doc.scrollWidth, clientWidth: doc.clientWidth, wide: wide.slice(0, 8), fonts: [...new Set(fonts)] };
      });
      console.log(`${basename(file)} ${label}: overflow=${res.scrollWidth > res.clientWidth + 1 ? res.scrollWidth - res.clientWidth + "px" : "none"} fonts=${res.fonts.join(",")} errors=${errors.length}`);
      for (const w of res.wide) console.log("   wide:", w);
      for (const e of errors.slice(0, 10)) console.log("   error:", e);
      await page.close();
    }
  }
} else if (cmd === "figs") {
  const [file, ...ids] = pos;
  const book = basename(file, ".html");
  const dir = resolve(ROOT, "qa", book);
  mkdirSync(dir, { recursive: true });
  for (const dark of [false, true]) {
    if (dark && flags["light-only"]) continue;
    const { page } = await open(file, { width: Number(flags.width || 1280), dark });
    const list = ids.length ? ids : await page.$$eval("figure.fig", fs => fs.map(f => f.id));
    for (const id of list) {
      const el = await page.$("#" + id);
      if (!el) { console.log("missing", id); continue; }
      await el.scrollIntoView();
      const out = resolve(dir, `${id}${dark ? "-dark" : ""}.png`);
      await el.screenshot({ path: out });
      console.log(out);
    }
    await page.close();
  }
} else if (cmd === "el") {
  const [file, selector, name = "el"] = pos;
  const book = basename(file, ".html");
  const dir = resolve(ROOT, "qa", book);
  mkdirSync(dir, { recursive: true });
  const { page } = await open(file, { width: Number(flags.width || 1280), dark: !!flags.dark, print: !!flags.print });
  const el = await page.$(selector);
  if (!el) { console.log("missing", selector); }
  else {
    await el.scrollIntoView();
    const out = resolve(dir, `${name}.png`);
    await el.screenshot({ path: out });
    console.log(out);
  }
  await page.close();
} else if (cmd === "pdf") {
  mkdirSync(resolve(ROOT, "pdf"), { recursive: true });
  for (const file of pos) {
    const { page, errors } = await open(file, { width: 1000, print: true });
    const out = resolve(ROOT, "pdf", basename(file, ".html") + ".pdf");
    await page.pdf({ path: out, preferCSSPageSize: true, printBackground: true, outline: true, tagged: true, timeout: 300000 });
    console.log(out, errors.length ? "errors: " + errors.join(" | ") : "");
    await page.close();
  }
}
await browser.close();
