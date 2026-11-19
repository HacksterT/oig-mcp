// Build the hackathon deck from docs/submission/deck.md (speaker notes) and the
// slide text below. From this folder: npm ci && node build_pptx.js
// Output: out/oig-mcp-deck.pptx
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const lu = require("react-icons/lu");

const JSZip = require("jszip");
const REPO = path.resolve(__dirname, "../../..");

// pptxgenjs writes Office's stock theme; write this deck's colors and fonts into it.
async function applyTheme(file, theme) {
  const zip = await JSZip.loadAsync(fs.readFileSync(file));
  const names = Object.keys(zip.files).filter((n) => /^ppt\/theme\/theme\d+\.xml$/.test(n));
  const order = ["dk1", "lt1", "dk2", "lt2", "accent1", "accent2", "accent3", "accent4", "accent5", "accent6", "hlink", "folHlink"];
  const scheme = `<a:clrScheme name="${theme.name}">` +
    order.map((k) => `<a:${k}><a:srgbClr val="${theme.colors[k]}"/></a:${k}>`).join("") + "</a:clrScheme>";
  for (const n of names) {
    let xml = await zip.file(n).async("string");
    xml = xml.replace(/<a:clrScheme[\s\S]*?<\/a:clrScheme>/, scheme);
    xml = xml.replace(/(<a:majorFont>\s*<a:latin typeface=")[^"]*/, `$1${theme.headFontFace}`);
    xml = xml.replace(/(<a:minorFont>\s*<a:latin typeface=")[^"]*/, `$1${theme.bodyFontFace}`);
    zip.file(n, xml);
  }
  fs.writeFileSync(file, await zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE" }));
}
const IMG = path.join(REPO, "docs/submission/images");
const OUT = path.join(__dirname, "out");

// ---------- palette: evergreen ink, teal, amber ----------
const HEX = {
  ink: "14302E", teal: "2A6F6A", amber: "E3A33B", tint: "EEF4F3", white: "FFFFFF",
  sage: "8FB3AE", coral: "C8553D", muted: "5F7371", gray: "B9C9C6", text: "26302F",
  inkSoft: "1E4643", rule: "D5E0DE",
};
const THEME = {
  name: "OIG Oversight",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: HEX.ink, lt1: HEX.white, dk2: HEX.teal, lt2: HEX.tint,
    accent1: HEX.amber, accent2: HEX.teal, accent3: HEX.sage, accent4: HEX.coral,
    accent5: HEX.muted, accent6: HEX.gray, hlink: HEX.teal, folHlink: HEX.muted,
  },
};

// ---------- speaker notes from deck.md ----------
const md = fs.readFileSync(path.join(REPO, "docs/submission/deck.md"), "utf8");
const NOTES = {};
for (const block of md.split(/\n## Slide /).slice(1)) {
  const n = parseInt(block, 10);
  const m = block.match(/\*\*Speaker notes:\*\*\s*([\s\S]*?)(\n---|\n## |$)/);
  NOTES[n] = m ? m[1].trim() : "";
}

// ---------- icons ----------
async function iconPng(name, color, px = 256) {
  const Comp = lu[name];
  if (!Comp) throw new Error("missing icon " + name);
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, { color: "#" + color, size: px }));
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}
const ICONS = {};
async function icon(name, color) {
  const k = name + color;
  if (!ICONS[k]) ICONS[k] = await iconPng(name, color);
  return ICONS[k];
}

(async () => {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_16x9"; // 10 x 5.625
  pres.author = "Troy Sybert";
  pres.title = "VA OIG Oversight Assistant";
  pres.subject = "GSA MCP Server and AI Agent Government Hackathon";
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  const C = pres.SchemeColor;

  // ---------- layouts ----------
  const footer = (color) => [
    { text: { text: "VA OIG Oversight Assistant  ·  oig-mcp", options: { x: 0.5, y: 5.2, w: 5, h: 0.25, fontSize: 9, color, margin: 0 } } },
  ];
  pres.defineSlideMaster({
    title: "TITLE_DARK",
    background: { color: HEX.ink },
    objects: [
      { placeholder: { options: { name: "kicker", type: "body", x: 0.6, y: 0.95, w: 8.8, h: 0.3, fontSize: 10.5, bold: true, color: C.accent1, charSpacing: 3, margin: 0 }, text: "" } },
      { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 1.3, w: 8.8, h: 1.0, fontFace: "Cambria", fontSize: 44, bold: true, color: C.background1, margin: 0, valign: "top", align: "left" }, text: "" } },
      { placeholder: { options: { name: "body", type: "body", x: 0.6, y: 2.35, w: 7.6, h: 0.8, fontSize: 17, italic: true, color: C.accent3, margin: 0, valign: "top" }, text: "" } },
    ],
  });
  pres.defineSlideMaster({
    title: "CONTENT",
    background: { color: HEX.white },
    margin: [0.5, 0.5, 0.5, 0.5],
    objects: [
      { placeholder: { options: { name: "kicker", type: "body", x: 0.5, y: 0.32, w: 9, h: 0.26, fontSize: 10, bold: true, color: C.accent1, charSpacing: 3, margin: 0 }, text: "" } },
      { placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.58, w: 9, h: 0.62, fontFace: "Cambria", fontSize: 28, bold: true, color: C.text1, margin: 0, valign: "top", align: "left" }, text: "" } },
      ...footer(HEX.muted),
    ],
    slideNumber: { x: 9.0, y: 5.2, w: 0.5, h: 0.25, fontSize: 9, color: HEX.muted, align: "right" },
  });
  pres.defineSlideMaster({
    title: "CONTENT_DARK",
    background: { color: HEX.ink },
    objects: [
      { placeholder: { options: { name: "kicker", type: "body", x: 0.5, y: 0.32, w: 9, h: 0.26, fontSize: 10, bold: true, color: C.accent1, charSpacing: 3, margin: 0 }, text: "" } },
      { placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.58, w: 9, h: 0.62, fontFace: "Cambria", fontSize: 28, bold: true, color: C.background1, margin: 0, valign: "top", align: "left" }, text: "" } },
      ...footer(HEX.sage),
    ],
    slideNumber: { x: 9.0, y: 5.2, w: 0.5, h: 0.25, fontSize: 9, color: HEX.sage, align: "right" },
  });

  // ---------- helpers ----------
  let cur = { n: 0, section: "" };
  function newSlide(master, kicker, title, section) {
    if (section && section !== cur.section) { pres.addSection({ title: section }); cur.section = section; }
    cur.n += 1;
    const s = pres.addSlide({ masterName: master, sectionTitle: cur.section });
    if (kicker) s.addText(kicker, { placeholder: "kicker" });
    if (title) s.addText(title, { placeholder: "title" });
    if (NOTES[cur.n]) s.addNotes(NOTES[cur.n]);
    return s;
  }
  const T = (s, text, o) => s.addText(text, { isTextBox: true, margin: 0, valign: "top", fontSize: 14, color: C.text1, ...o });
  async function iconDot(s, name, x, y, d, fill, fg, objectName) {
    s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: fill }, line: { color: fill }, objectName });
    const pad = d * 0.24;
    s.addImage({ data: await icon(name, fg), x: x + pad, y: y + pad, w: d - 2 * pad, h: d - 2 * pad, altText: name.replace(/^Lu/, "") + " icon" });
  }
  function card(s, x, y, w, h, fill = C.background2, objectName) {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: fill }, line: { color: fill }, objectName });
  }
  function chip(s, text, x, y, w, h, fill, color, o = {}) {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: h / 2, fill: { color: fill }, line: { color: fill } });
    s.addText(text, { isTextBox: true, x, y, w, h, margin: 0, align: "center", valign: "middle", fontSize: 11, bold: true, color, ...o });
  }
  function numDot(s, n, x, y, d, fill, color) {
    s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: fill }, line: { color: fill } });
    s.addText(String(n), { isTextBox: true, x, y, w: d, h: d, margin: 0, align: "center", valign: "middle", fontSize: 13, bold: true, color, fontFace: "Cambria" });
  }
  function placeholderBox(s, x, y, w, h, label, dark = false) {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y, w, h, rectRadius: 0.08, fill: { color: dark ? HEX.inkSoft : HEX.tint },
      line: { color: dark ? HEX.sage : HEX.teal, width: 1.25, dashType: "dash" }, objectName: "Screenshot placeholder",
    });
    s.addText(label, { isTextBox: true, x: x + 0.3, y, w: w - 0.6, h, margin: 0, align: "center", valign: "middle", fontSize: 12, italic: true, color: dark ? HEX.sage : HEX.teal });
  }
  const arrow = (s, x1, y1, x2, y2, both = false, color = HEX.teal) =>
    s.addShape(pres.shapes.LINE, { x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1) || 0.001, h: Math.abs(y2 - y1) || 0.001, flipH: x2 < x1, flipV: y2 < y1,
      line: { color, width: 1.75, endArrowType: "triangle", beginArrowType: both ? "triangle" : undefined } });
  const chartText = { catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", dataLabelFontFace: "+mn-lt", titleFontFace: "+mn-lt", legendFontFace: "+mn-lt" };
  const chartQuiet = {
    ...chartText, catAxisLabelColor: HEX.muted, valAxisLabelColor: HEX.muted, catAxisLabelFontSize: 11, valAxisLabelFontSize: 10,
    valGridLine: { color: HEX.rule, size: 0.75 }, catGridLine: { style: "none" }, dataLabelFontSize: 11, dataLabelColor: HEX.text,
    catAxisLineShow: false, valAxisLineShow: false,
  };

  // ===== 1. Title =====
  {
    const s = newSlide("TITLE_DARK", "GSA MCP SERVER AND AI AGENT GOVERNMENT HACKATHON  ·  DATASET ACCESS TRACK", "VA OIG Oversight Assistant", "Opening");
    s.addText("An MCP server that lets any AI agent answer questions across VA Inspector General reports, with a citation for every finding", { placeholder: "body" });
    const stats = [["4,410", "reports"], ["15,649", "recommendations"], ["11,264", "facility responses"]];
    stats.forEach(([v, l], i) => {
      const x = 0.6 + i * 2.55;
      T(s, v, { x, y: 3.45, w: 2.4, h: 0.6, fontFace: "Cambria", fontSize: 34, bold: true, color: C.accent1 });
      T(s, l, { x, y: 4.05, w: 2.4, h: 0.3, fontSize: 13, color: C.background1 });
    });
    T(s, "Troy Sybert, MD   ·   github.com/HacksterT/oig-mcp   ·   Deployed in IBM watsonx Orchestrate", { x: 0.6, y: 4.85, w: 8.8, h: 0.3, fontSize: 11, color: C.accent3 });
  }

  // ===== 2. Challenge =====
  {
    const s = newSlide("CONTENT", "THE CHALLENGE", "A public record built for reading, not for questions", "Opening");
    card(s, 0.5, 1.45, 2.55, 3.55, C.text1, "Record size panel");
    [["4,410", "reports at vaoig.gov"], ["15,649", "recommendations"], ["11,264", "facility responses, inside report PDFs"]].forEach(([v, l], i) => {
      T(s, v, { x: 0.75, y: 1.65 + i * 1.08, w: 2.1, h: 0.5, fontFace: "Cambria", fontSize: 28, bold: true, color: C.accent1 });
      T(s, l, { x: 0.75, y: 2.13 + i * 1.08, w: 2.1, h: 0.45, fontSize: 12, color: C.background1 });
    });
    const items = [
      ["LuPlug", "No machine access", "No API or bulk export, so no AI assistant can work with the record directly."],
      ["LuFileText", "Answers live inside PDFs", "What a facility committed to do, and by when, appears only in report PDFs."],
      ["LuSearch", "Search finds documents", "Not patterns: it cannot answer \u201Cwhat keeps being cited?\u201D or \u201Cis this growing year over year?\u201D"],
      ["LuUsers", "The work falls on people", "Staff read prior reports by hand to learn what OIG found at their facility and its peers."],
    ];
    for (const [k, it] of items.entries()) {
      const col = k % 2, row = Math.floor(k / 2);
      const x = 3.35 + col * 3.1, y = 1.45 + row * 1.82;
      card(s, x, y, 2.9, 1.7, C.background2, "Problem card");
      await iconDot(s, it[0], x + 0.2, y + 0.2, 0.5, HEX.teal, HEX.white, "Problem icon");
      T(s, it[1], { x: x + 0.82, y: y + 0.2, w: 1.95, h: 0.55, fontSize: 14, bold: true, valign: "middle" });
      T(s, it[2], { x: x + 0.2, y: y + 0.85, w: 2.55, h: 0.8, fontSize: 12, color: C.text1 });
    }
  }

  // ===== 3. Solution =====
  {
    const s = newSlide("CONTENT", "THE SOLUTION", "One MCP server over the whole OIG record", "Opening");
    const rows = [
      ["LuMessageSquare", "Ask in plain language", "Exact counts, trends, time to close, recurring findings, and peer commitments, across every report."],
      ["LuLink", "Every finding can be checked", "An OIG report number, a vaoig.gov link, and the date the data was collected."],
      ["LuBan", "It states its limits", "No facility ratings, no predictions, no deadline miss rates, no guessing who was responsible."],
      ["LuPlug", "It runs anywhere MCP does", "Deployed in IBM watsonx Orchestrate; works with Claude and other MCP clients."],
    ];
    for (const [i, r] of rows.entries()) {
      const y = 1.45 + i * 0.9;
      await iconDot(s, r[0], 0.5, y, 0.55, HEX.tint, HEX.teal, "Feature icon");
      T(s, r[1], { x: 1.25, y: y - 0.02, w: 3.9, h: 0.3, fontSize: 14, bold: true });
      T(s, r[2], { x: 1.25, y: y + 0.28, w: 3.9, h: 0.55, fontSize: 12, color: C.accent5 });
    }
    T(s, "QUESTIONS IT ANSWERS", { x: 5.6, y: 1.45, w: 3.9, h: 0.25, fontSize: 10, bold: true, color: C.text2, charSpacing: 2 });
    const qs = [
      "Which findings recur across VA medical facilities?",
      "How many suicide prevention findings has OIG made each year since 2020?",
      "What did peer facilities commit to doing when cited for unsecured medication carts?",
      "Prepare a brief for the Durham VA Medical Center's next inspection.",
    ];
    qs.forEach((q, i) => {
      const x = 5.6 + (i % 2) * 0.35, y = 1.8 + i * 0.8;
      card(s, x, y, 3.55, 0.66, i % 2 ? C.background2 : C.text1, "Question bubble");
      T(s, "“" + q + "”", { x: x + 0.18, y, w: 3.2, h: 0.66, fontSize: 12, italic: true, valign: "middle", color: i % 2 ? C.text1 : C.background1 });
    });
  }

  // ===== 4. Who it serves =====
  {
    const s = newSlide("CONTENT", "MISSION", "Oversight that facilities can learn from", "Opening");
    const cards = [
      ["LuHospital", "Facility patient safety and quality staff", "Preparing for an OIG inspection: their open and repeat findings, the most common findings at peer inspections, and what peers committed to do."],
      ["LuLandmark", "Program offices", "Whether a finding is isolated or systemic before a national fix, and how long similar recommendations take to close."],
      ["LuScale", "Oversight and policy staff", "What is open and aging, by office, topic, or report type, reconciled with OIG's own published counts."],
    ];
    for (const [i, c] of cards.entries()) {
      const x = 0.5 + i * 3.05;
      card(s, x, 1.45, 2.85, 2.55, C.background2, "User card");
      await iconDot(s, c[0], x + 0.25, 1.65, 0.6, HEX.teal, HEX.white, "User icon");
      T(s, c[1], { x: x + 0.25, y: 2.35, w: 2.4, h: 0.55, fontSize: 14, bold: true });
      T(s, c[2], { x: x + 0.25, y: 2.92, w: 2.4, h: 1.05, fontSize: 11.5, color: C.text1 });
    }
    card(s, 0.5, 4.2, 9, 0.8, C.text1, "Trust note");
    s.addText([
      { text: "Trust over polish.  ", options: { bold: true, color: C.accent1 } },
      { text: "No facility scores or rankings. A repeat finding means the issue was cited again, not that nothing was done. A next-inspection date is labeled an estimate, because OIG publishes no schedule.", options: { color: C.background1 } },
    ], { isTextBox: true, x: 0.75, y: 4.2, w: 8.5, h: 0.8, margin: 0, valign: "middle", fontSize: 12 });
  }

  // ===== 5. Server design =====
  {
    const s = newSlide("CONTENT", "SERVER DESIGN", "Two parts, one origin", "Design");
    const boxes = [
      { x: 0.5, w: 1.45, head: "vaoig.gov", body: "OIG's published reports and PDFs", fill: C.background2, dark: false },
      { x: 2.4, w: 1.95, head: "Data service", body: "Crawler, SQLite, JSON API, behind Cloudflare Access", fill: C.background2, dark: false },
      { x: 4.8, w: 2.5, head: "oig-mcp", body: "7 tools · 3 resources · 2 prompts\nauth, rate limit, usage log, traces", fill: C.text1, dark: true },
      { x: 7.75, w: 1.75, head: "Any MCP host", body: "Orchestrate, Claude, any MCP client", fill: C.background2, dark: false },
    ];
    const by = 1.55, bh = 1.45;
    boxes.forEach((b) => {
      card(s, b.x, by, b.w, bh, b.fill, b.head + " box");
      T(s, b.head, { x: b.x + 0.15, y: by + 0.15, w: b.w - 0.3, h: 0.35, fontSize: 15, bold: true, fontFace: "Cambria", color: b.dark ? C.accent1 : C.text1 });
      T(s, b.body, { x: b.x + 0.15, y: by + 0.55, w: b.w - 0.3, h: 0.85, fontSize: 11, color: b.dark ? C.background1 : C.text1 });
    });
    const ay = by + bh / 2;
    arrow(s, 1.98, ay, 2.37, ay, false);
    arrow(s, 4.38, ay, 4.77, ay, true);
    arrow(s, 7.33, ay, 7.72, ay, true);
    const lab = (t, x, w) => T(s, t, { x, y: by + bh + 0.08, w, h: 0.45, fontSize: 9.5, italic: true, color: C.accent5, align: "center" });
    lab("crawled and parsed", 1.45, 1.45);
    lab("HTTPS, service token and API key", 3.55, 2.05);
    lab("stdio or Streamable HTTP", 6.75, 1.6);
    const facts = [
      ["LuBraces", "Python on FastMCP", "One tool per file, each registering itself."],
      ["LuLock", "One outbound origin", "Set by the operator, never by a tool argument, through one hardened HTTP client."],
      ["LuWaypoints", "Two transports, same code", "stdio inside Orchestrate and desktop hosts; Streamable HTTP for testers and judges."],
    ];
    for (const [i, f] of facts.entries()) {
      const x = 0.5 + i * 3.05;
      await iconDot(s, f[0], x, 3.75, 0.45, HEX.amber, HEX.ink, "Design fact icon");
      T(s, f[1], { x: x + 0.6, y: 3.72, w: 2.3, h: 0.3, fontSize: 13, bold: true });
      T(s, f[2], { x: x + 0.6, y: 4.03, w: 2.3, h: 0.9, fontSize: 11, color: C.accent5 });
    }
  }

  // ===== 6. Key decision 1 =====
  {
    const s = newSlide("CONTENT", "KEY DECISION 1", "Tools built around the user's goal", "Design");
    const tools = [
      ["vaoig_get_dataset_status", "How current the data is; valid filter values"],
      ["vaoig_search_findings", "Findings, and what peers committed to do"],
      ["vaoig_analyze_recommendations", "Exact counts, trends, time to close, aging"],
      ["vaoig_find_systemic_clusters", "Findings that recur, and how common each is"],
      ["vaoig_get_report", "One report in full, with facility responses"],
      ["vaoig_get_facility_profile", "One facility's reports and repeat findings"],
      ["vaoig_get_inspection_brief", "Prepare one facility for inspection"],
    ];
    tools.forEach(([name, what], i) => {
      const y = 1.42 + i * 0.5;
      card(s, 0.5, y, 5.7, 0.42, i % 2 ? C.background1 : C.background2, "Tool row");
      T(s, name, { x: 0.65, y, w: 2.75, h: 0.42, fontFace: "Consolas", fontSize: 10.5, bold: true, color: C.text2, valign: "middle" });
      T(s, what, { x: 3.45, y, w: 2.7, h: 0.42, fontSize: 11, valign: "middle" });
    });
    card(s, 6.5, 1.42, 3.0, 1.55, C.text1, "Inspection brief stat");
    T(s, "1 call", { x: 6.7, y: 1.55, w: 2.6, h: 0.6, fontFace: "Cambria", fontSize: 32, bold: true, color: C.accent1 });
    T(s, "instead of up to ten searches: the inspection brief does the sequencing a weaker model gets wrong.", { x: 6.7, y: 2.15, w: 2.65, h: 0.8, fontSize: 11.5, color: C.background1 });
    T(s, [
      { text: "Exact answers by design. ", options: { bold: true } },
      { text: "Counts come from the analysis tool, never from adding up search results.", options: { breakLine: true } },
      { text: " ", options: { breakLine: true, fontSize: 6 } },
      { text: "Precise names. ", options: { bold: true } },
      { text: "A shared vaoig_ prefix and a verb, so the right tool is obvious in any host's list." },
    ], { x: 6.5, y: 3.15, w: 3.0, h: 1.85, fontSize: 12 });
  }

  // ===== 7. Key decision 2 =====
  {
    const s = newSlide("CONTENT", "KEY DECISION 2", "Typed, bounded contracts in both directions", "Design");
    const cards = [
      ["Inputs", "Enums for closed sets; unknown filters refused, not dropped; every list, string, and offset bounded."],
      ["Outputs", "Every tool declares an output schema, so clients see each result's shape in the tool list."],
      ["Errors the agent can act on", "An MCP error result with a hint chosen by cause. \"Not found\" and \"several match\" are answers, not errors."],
      ["Corrected at the boundary", "A misplaced filter is refused with the fix; an empty result says to check filter values first."],
    ];
    cards.forEach(([h, b], k) => {
      const x = 0.5 + (k % 2) * 2.85, y = 1.42 + Math.floor(k / 2) * 1.8;
      card(s, x, y, 2.7, 1.68, C.background2, "Contract card");
      numDot(s, k + 1, x + 0.18, y + 0.18, 0.4, HEX.amber, HEX.ink);
      T(s, h, { x: x + 0.7, y: y + 0.16, w: 1.9, h: 0.45, fontSize: 13, bold: true, valign: "middle" });
      T(s, b, { x: x + 0.18, y: y + 0.7, w: 2.38, h: 0.95, fontSize: 11 });
    });
    card(s, 6.35, 1.42, 3.15, 3.48, C.text1, "Boundary example");
    T(s, "FROM EVALUATION", { x: 6.6, y: 1.6, w: 2.7, h: 0.25, fontSize: 9.5, bold: true, color: C.accent1, charSpacing: 2 });
    T(s, "The agent put an office's full name in the domain filter:", { x: 6.6, y: 1.92, w: 2.7, h: 0.5, fontSize: 11, color: C.accent3 });
    T(s, "domain = \"Veterans Benefits\n         Administration\"", { x: 6.6, y: 2.45, w: 2.75, h: 0.55, fontFace: "Consolas", fontSize: 10.5, color: C.background1 });
    T(s, "Before: it matched nothing, and the agent told the user there was no data. Now the server refuses it with the fix:", { x: 6.6, y: 3.07, w: 2.7, h: 0.75, fontSize: 11, color: C.accent3 });
    chip(s, "Use action_office='VBA' instead", 6.55, 3.95, 2.8, 0.42, HEX.amber, HEX.ink, { fontFace: "Consolas", fontSize: 9 });
    T(s, "GPT-OSS 120B in watsonx Orchestrate", { x: 6.6, y: 4.47, w: 2.7, h: 0.3, fontSize: 9.5, italic: true, color: C.accent3 });
  }

  // ===== 8. Key decision 3 =====
  {
    const s = newSlide("CONTENT", "KEY DECISION 3", "Trust carried in every answer, by the server", "Design");
    T(s, "Guardrails live in the server's instructions and results, not in one host's system prompt, so they hold for every agent that connects.", { x: 0.5, y: 1.35, w: 9, h: 0.5, fontSize: 13, italic: true, color: C.text2 });
    const rows = [
      ["LuFileSearch", "Provenance", "The data date, whether it is stale, and a report number and vaoig.gov link on every record."],
      ["LuTriangleAlert", "Notices", "Caveats the agent must pass on, such as why OIG's dashboard shows 586 open recommendations and this data 567."],
      ["LuShieldCheck", "Scope", "No medical, benefits, or legal advice; emergencies sent to 911; no rankings or forecasts; never a guess at who was responsible."],
      ["LuQuote", "Quoted text", "Fields that quote OIG reports are named, to be cited, never followed. Every tool is read-only."],
      ["LuHand", "Ambiguity", "A facility name that matches several is handed back to the user, never resolved by the model."],
    ];
    for (const [i, r] of rows.entries()) {
      const col = i < 3 ? 0 : 1, row = i < 3 ? i : i - 3;
      const x = 0.5 + col * 4.6, y = 2.0 + row * 1.0;
      await iconDot(s, r[0], x, y, 0.5, i % 2 ? HEX.amber : HEX.teal, i % 2 ? HEX.ink : HEX.white, "Trust icon");
      T(s, r[1], { x: x + 0.65, y: y - 0.02, w: 3.75, h: 0.28, fontSize: 13.5, bold: true });
      T(s, r[2], { x: x + 0.65, y: y + 0.27, w: 3.75, h: 0.68, fontSize: 11, color: C.accent5 });
    }
    card(s, 5.1, 4.05, 4.4, 0.95, C.text1, "One instruction");
    T(s, [
      { text: "That is why the Orchestrate agent needs one instruction: ", options: { color: C.background1 } },
      { text: "answer only from what the tools return.", options: { color: C.accent1, bold: true } },
    ], { x: 5.3, y: 4.05, w: 4.05, h: 0.95, fontSize: 12, valign: "middle" });
  }

  // ===== 9. Elicitation =====
  {
    const s = newSlide("CONTENT", "ASKING THE USER, NEVER GUESSING", "MCP elicitation, with a fallback for every host", "Design");
    card(s, 0.5, 1.4, 4.5, 0.5, C.text1, "User question");
    T(s, "“What has OIG found at the Columbia VA?”", { x: 0.7, y: 1.4, w: 4.2, h: 0.5, fontSize: 13, italic: true, color: C.background1, valign: "middle" });
    [["544", "SC"], ["589A4", "MO"], ["688", "DC"]].forEach(([st, loc], i) => chip(s, st + "  " + loc, 0.5 + i * 1.53, 2.1, 1.4, 0.36, HEX.amber, HEX.ink, { fontSize: 11 }));
    T(s, "Three facilities match. Findings from the wrong one would be credited to the facility the user meant.", { x: 0.5, y: 2.55, w: 4.5, h: 0.45, fontSize: 11, color: C.accent5 });
    const br = [
      ["Host shows MCP forms", "The server pauses the call and asks the user. Only a matching station is accepted, and the result tells the AI the user chose.", C.background2],
      ["Any other host", "The matches come back with a next step: do not choose; list them, ask, and call again with the station number.", C.background2],
    ];
    br.forEach(([h, b, f], i) => {
      const x = 0.5 + i * 2.3;
      card(s, x, 3.12, 2.2, 1.85, f, "Branch card");
      T(s, (i ? "FALLBACK" : "ELICITATION"), { x: x + 0.15, y: 3.25, w: 1.9, h: 0.22, fontSize: 9, bold: true, color: C.accent1, charSpacing: 2 });
      T(s, h, { x: x + 0.15, y: 3.48, w: 1.95, h: 0.3, fontSize: 12.5, bold: true });
      T(s, b, { x: x + 0.15, y: 3.8, w: 1.95, h: 1.15, fontSize: 10.5 });
    });
    // chart: before vs after
    s.addChart(pres.charts.BAR, [
      { name: "Claude asks in chat", labels: ["Model requests", "Calls to the server", "User turns"], values: [4, 2, 2] },
      { name: "The server's form", labels: ["Model requests", "Calls to the server", "User turns"], values: [2, 1, 1] },
    ], {
      x: 5.3, y: 1.35, w: 4.2, h: 2.25, barDir: "bar", barGrouping: "clustered", chartColors: [HEX.gray, HEX.teal],
      ...chartQuiet, showValue: true, dataLabelPosition: "outEnd", valAxisHidden: true, valGridLine: { style: "none" },
      showLegend: true, legendPos: "b", legendFontSize: 10, legendColor: HEX.muted, catAxisOrientation: "maxMin", barGapWidthPct: 60,
      valAxisMinVal: 0, valAxisMaxVal: 5, objectName: "Elicitation savings chart",
    });
    T(s, "39%", { x: 5.4, y: 3.7, w: 1.5, h: 0.7, fontFace: "Cambria", fontSize: 38, bold: true, color: C.accent1 });
    T(s, "fewer tokens: 47,607 to 29,046, median of five runs each way, Claude Opus 5.5", { x: 6.95, y: 3.78, w: 2.55, h: 0.65, fontSize: 11 });
    T(s, "Shown in Claude Code. Hosts implement MCP unevenly: Claude Desktop accepts URL mode only, and Orchestrate declared no elicitation, so safety cannot depend on the form alone.", { x: 5.4, y: 4.45, w: 4.1, h: 0.6, fontSize: 9.5, italic: true, color: C.accent5 });
  }

  // ===== 10. Orchestrate =====
  {
    const s = newSlide("CONTENT", "DEPLOYMENT", "Deployed in IBM watsonx Orchestrate", "Design");
    const rows = [
      ["LuTerminal", "Local toolkit", "Orchestrate runs the server over stdio inside its own runtime, with no network endpoint of its own."],
      ["LuKeyRound", "Credentials from a connection", "The data address and keys come from a key_value connection, never code or the repository."],
      ["LuBot", "A minimal agent", "GPT-OSS 120B, the seven tools, and one instruction: answer only from what the OIG tools return."],
      ["LuClipboardCheck", "Evaluated in place", "IBM's Agent Development Kit ran the gold questions in two rounds: three runs, then two."],
      ["LuActivity", "Traced end to end", "Each request carries a trace ID to the data service, so every conversation can be checked."],
    ];
    for (const [i, r] of rows.entries()) {
      const y = 1.4 + i * 0.73;
      await iconDot(s, r[0], 0.5, y, 0.48, HEX.tint, HEX.teal, "Deployment icon");
      T(s, r[1], { x: 1.13, y: y - 0.03, w: 3.6, h: 0.27, fontSize: 13, bold: true });
      T(s, r[2], { x: 1.13, y: y + 0.24, w: 3.6, h: 0.46, fontSize: 10.5, color: C.accent5 });
    }
    card(s, 4.95, 1.35, 4.55, 3.7, C.background2, "Orchestrate screenshot frame");
    s.addImage({ path: path.join(IMG, "orchestrate-answer.png"), x: 5.27, y: 1.47, w: 3.91, h: 3.33, altText: "watsonx Orchestrate Live Preview: GPT-OSS 120B answers What has OIG found at the Mountain Home VA? with a list of OIG report numbers and vaoig.gov links, ending with the data date 2026-11-04" });
    T(s, "GPT-OSS 120B in watsonx Orchestrate: every report cited, data date stated", { x: 4.95, y: 4.82, w: 4.55, h: 0.22, fontSize: 9, italic: true, color: C.accent5, align: "center" });
  }

  // ===== 11. Demo =====
  {
    const s = newSlide("CONTENT_DARK", "DEMO  ·  THE VIDEO IN SIX MOMENTS", "One quality manager, one question", "Demo");
    const steps = [
      ["Search vaoig.gov for \u201CMountain Home\u201D", "196 results, 20 a page; the detail sits in PDFs"],
      ["From PDFs to answers", "Pipeline and database, checked row by row against OIG"],
      ["Same server, three hosts", "Orchestrate, Claude Code over stdio, Hermes over HTTP"],
      ["\u201CThe Tennessee VA\u201D matches three", "The server's form asks which; he picks Mountain Home"],
      ["One brief", "Record, estimated window, top peer finding, peer actions"],
      ["\u201CWhich VA facility is the worst?\u201D", "Declined, with what the record can support instead"],
    ];
    steps.forEach(([q, what], i) => {
      const y = 1.32 + i * 0.6;
      numDot(s, i + 1, 0.5, y + 0.03, 0.4, i === 5 ? HEX.coral : HEX.amber, HEX.ink);
      T(s, q, { x: 1.05, y, w: 3.75, h: 0.27, fontSize: 11.5, bold: true, color: C.background1 });
      T(s, what, { x: 1.05, y: y + 0.26, w: 3.75, h: 0.32, fontSize: 9.5, color: C.accent3 });
    });
    const shots = [
      ["demo-search.png", "1  vaoig.gov: 196 results", "vaoig.gov search results for Mountain Home, displaying 1 to 20 of 196"],
      ["demo-elicitation.png", "4  The server's form", "Claude Code: MCP server oig-mcp requests your input; three Tennessee facilities to choose from"],
      ["demo-brief.png", "5  The brief", "Claude Code: the inspection brief for James H. Quillen VA Medical Center, station 621"],
      ["demo-refusal.png", "6  The refusal", "Hermes Agent with DeepSeek V4 Pro declines to name a worst facility and offers recurring findings instead"],
    ];
    shots.forEach(([f, cap, alt], k) => {
      const x = 5.0 + (k % 2) * 2.27, y = 1.32 + Math.floor(k / 2) * 1.62;
      s.addImage({ path: path.join(IMG, f), x, y, w: 2.17, h: 1.22, altText: alt });
      T(s, cap, { x, y: y + 1.25, w: 2.17, h: 0.25, fontSize: 9, bold: true, color: C.accent3 });
    });
    T(s, "The video runs under three minutes; slide 12 and the evaluation document carry the detail.", { x: 5.0, y: 4.62, w: 4.5, h: 0.4, fontSize: 10, italic: true, color: C.accent1 });
  }

  // ===== 12. Inside the brief =====
  {
    const s = newSlide("CONTENT", "DEMO  ·  WHAT ONE CALL RETURNS", "Inside the inspection brief", "Demo");
    card(s, 0.45, 1.35, 5.5, 3.25, C.background2, "Brief screenshot frame");
    s.addImage({ path: path.join(IMG, "demo-brief.png"), x: 0.57, y: 1.47, w: 5.26, h: 2.96, altText: "Claude Code showing the inspection brief: the facility check, Mountain Home's record, the next inspection estimate, and the main weakness, test result communication" });
    T(s, "Claude Opus 5.5 in Claude Code, one call to vaoig_get_inspection_brief, data as of November 4, 2026", { x: 0.45, y: 4.66, w: 5.5, h: 0.35, fontSize: 9, italic: true, color: C.accent5 });
    const parts = [
      ["The facility check", "The result says the user chose station 621 on the server's form."],
      ["Its own record", "11 reports, 31 recommendations, none open, no repeat findings, with how a repeat is counted."],
      ["The next window, labeled", "About December 2028, from the last inspection plus a three-year cycle."],
      ["The most common peer finding", "Test result communication, in 21 of 112 inspection reports, and Mountain Home is in that group."],
      ["What peers committed to do", "Hampton's monthly audit of 50 patients' results; Shreveport's seven-day follow-up review. Each with its report link."],
    ];
    parts.forEach(([h, b], i) => {
      const y = 1.35 + i * 0.73;
      numDot(s, i + 1, 6.15, y + 0.02, 0.36, HEX.amber, HEX.ink);
      T(s, h, { x: 6.62, y, w: 2.9, h: 0.26, fontSize: 12, bold: true });
      T(s, b, { x: 6.62, y: y + 0.25, w: 2.9, h: 0.47, fontSize: 9.5, color: C.accent5 });
    });
  }

  // ===== 13. Evaluation setup =====
  {
    const s = newSlide("CONTENT", "EVALUATION  ·  SETUP", "Scored against SQL, not the API under test", "Evaluation");
    const stages = [
      ["Gold set", "24 questions + 6 adversarial; answers by SQL from a frozen snapshot"],
      ["Agent", "Only the server's tools; no project prompt, just the server's own instructions"],
      ["Scoring", "Code where it can; two judges from different model families where it cannot"],
      ["Phoenix", "Every run traced and kept; IBM's ADK for the Orchestrate agent"],
    ];
    stages.forEach(([h, b], i) => {
      const x = 0.5 + i * 2.33;
      card(s, x, 1.38, 2.05, 1.32, i === 0 ? C.text1 : C.background2, "Pipeline stage");
      T(s, h, { x: x + 0.15, y: 1.48, w: 1.8, h: 0.3, fontSize: 13.5, bold: true, fontFace: "Cambria", color: i === 0 ? C.accent1 : C.text1 });
      T(s, b, { x: x + 0.15, y: 1.8, w: 1.8, h: 0.88, fontSize: 10.5, color: i === 0 ? C.background1 : C.text1 });
      if (i < 3) arrow(s, x + 2.07, 2.04, x + 2.31, 2.04, false);
    });
    s.addChart(pres.charts.BAR, [{ name: "Questions", labels: ["Exact figures", "Adversarial", "Behavior", "Lists", "Search", "Workflow"], values: [14, 6, 5, 2, 2, 1] }], {
      x: 0.4, y: 2.85, w: 4.3, h: 2.2, barDir: "bar", chartColors: [HEX.teal], ...chartQuiet, showValue: true, dataLabelPosition: "outEnd",
      valAxisHidden: true, valGridLine: { style: "none" }, showLegend: false, catAxisOrientation: "maxMin", barGapWidthPct: 45,
      showTitle: true, title: "The 30 questions, by kind", titleFontSize: 11, titleColor: HEX.text, objectName: "Question mix chart",
    });
    const ar = 1900 / 1100, ih = 1.95, iw = ih * ar;
    s.addImage({ path: path.join(IMG, "phoenix-trace.png"), x: 9.5 - iw, y: 2.88, w: iw, h: ih, altText: "One question traced in Phoenix: Llama 3.3 70B on watsonx.ai lists the server's tools, calls vaoig_analyze_recommendations, and answers" });
    T(s, "One question traced in Phoenix: Llama 3.3 70B on watsonx.ai calls the analysis tool and answers", { x: 9.5 - iw, y: 4.86, w: iw, h: 0.25, fontSize: 9, italic: true, color: C.accent5 });
  }

  // ===== 14. Results =====
  {
    const s = newSlide("CONTENT", "EVALUATION  ·  RESULTS", "What the server adds", "Evaluation");
    s.addChart(pres.charts.BAR, [
      { name: "No tools", labels: ["Claude Opus 5.5", "Llama 3.3 70B"], values: [3, 2] },
      { name: "With the server", labels: ["Claude Opus 5.5", "Llama 3.3 70B"], values: [23, 9] },
    ], {
      x: 0.4, y: 1.3, w: 4.6, h: 3.3, barDir: "col", barGrouping: "clustered", chartColors: [HEX.gray, HEX.teal], ...chartQuiet,
      showValue: true, dataLabelPosition: "outEnd", valAxisMinVal: 0, valAxisMaxVal: 24, valAxisMajorUnit: 6, showLegend: true, legendPos: "b",
      legendFontSize: 10, legendColor: HEX.muted, barGapWidthPct: 70, showTitle: true, title: "Of 24 questions, passing every check", titleFontSize: 11, titleColor: HEX.text,
      objectName: "Server lift chart",
    });
    const tiles = [
      ["29 of 30", "Claude Opus 5.5 on the final server, adversarial questions included"],
      ["0", "cited reports that do not exist, in the server-backed Claude, Llama, and GPT-OSS runs"],
      ["89 of 90", "answers where the two judges, from different model families, agreed"],
      ["2,059", "of 2,059 calls answered, ramping from 1 to 40 concurrent clients"],
    ];
    tiles.forEach(([v, l], k) => {
      const x = 5.3 + (k % 2) * 2.15, y = 1.38 + Math.floor(k / 2) * 1.62;
      card(s, x, y, 2.0, 1.48, k === 0 ? C.text1 : C.background2, "Result tile");
      T(s, v, { x: x + 0.15, y: y + 0.12, w: 1.75, h: 0.55, fontFace: "Cambria", fontSize: 26, bold: true, color: k === 0 ? C.accent1 : C.text2 });
      T(s, l, { x: x + 0.15, y: y + 0.7, w: 1.75, h: 0.75, fontSize: 10, color: k === 0 ? C.background1 : C.text1 });
    });
    T(s, "Limits: one builder wrote the questions and the server, and fixes followed failures on these questions. Twenty-four questions are a check, not a statistical estimate. One load test, on one Mac, not run to failure.",
      { x: 0.5, y: 4.68, w: 9, h: 0.42, fontSize: 9.5, italic: true, color: C.accent5 });
  }

  // ===== 15. Five models =====
  {
    const s = newSlide("CONTENT", "EVALUATION  ·  FIVE MODELS", "One server, five models", "Evaluation");
    s.addChart(pres.charts.BAR, [{
      name: "Of 24 questions", labels: ["Claude Opus 5.5", "Claude Sonnet 5.5", "GPT-OSS 120B (Orchestrate), 2 runs", "Llama 3.3 70B (watsonx.ai)", "No server: Opus", "No server: Llama"],
      values: [23, 22, 12, 9, 3, 2],
    }], {
      x: 0.4, y: 1.3, w: 5.3, h: 3.15, barDir: "bar", chartColors: [HEX.teal, HEX.teal, HEX.amber, HEX.amber, HEX.gray, HEX.gray], ...chartQuiet,
      showValue: true, dataLabelPosition: "outEnd", valAxisHidden: true, valGridLine: { style: "none" }, valAxisMinVal: 0, valAxisMaxVal: 26,
      showLegend: false, catAxisOrientation: "maxMin", barGapWidthPct: 40, catAxisLabelFontSize: 10.5,
      showTitle: true, title: "Of 24 questions, passing every check, final server", titleFontSize: 11, titleColor: HEX.text, objectName: "Five models chart",
    });
    T(s, "GPT-OSS 120B: 12 and 12 in two runs. DeepSeek V4 Pro, scored differently: 18 of 18 agree with the gold.", { x: 0.5, y: 4.5, w: 5.2, h: 0.5, fontSize: 9.5, italic: true, color: C.accent5 });
    card(s, 6.0, 1.38, 3.5, 1.2, C.text1, "Lesson quote");
    T(s, "“A server that only meets the best model has not been tested.”", { x: 6.2, y: 1.38, w: 3.15, h: 1.2, fontFace: "Cambria", fontSize: 15, italic: true, bold: true, color: C.accent1, valign: "middle" });
    const pts = [
      ["Not the tool choice.", "Every model scored by code picked the right tool on 19 to 22 of 20 to 22 questions."],
      ["Using what the result carries.", "Citations: Claude 8 of 8; GPT-OSS and Llama 3 of 8."],
      ["Context limits.", "Llama overflowed 128K tokens, so results were cut 42 percent."],
      ["Staying in scope.", "Llama 0 of 6 adversarial, then 4 of 6 once the server stated its scope."],
    ];
    pts.forEach(([h, b], i) => T(s, [{ text: h + " ", options: { bold: true } }, { text: b }], { x: 6.0, y: 2.72 + i * 0.58, w: 3.5, h: 0.55, fontSize: 10.5 }));
  }

  // ===== 16. Failure analysis =====
  {
    const s = newSlide("CONTENT", "EVALUATION  ·  FAILURE ANALYSIS", "Every failure traced, fixed, and retested", "Evaluation");
    const rows = [
      ["Server", HEX.teal, "An office name in the wrong filter matched nothing", "Fixed in the server"],
      ["Data service", HEX.sage, "Counting with a response filter failed", "Fixed in the data service"],
      ["Model", HEX.amber, "Report numbers given without links", "Citation requested in every result"],
      ["Platform", HEX.gray, "Expired logins in Orchestrate", "Log in fresh before each run"],
      ["Scorer", HEX.coral, "Non-breaking hyphens in report numbers were missed", "Scorer fixed, every run rescored"],
    ];
    T(s, "CAUSE", { x: 0.5, y: 1.35, w: 1.3, h: 0.22, fontSize: 9, bold: true, color: C.accent5, charSpacing: 2 });
    T(s, "EXAMPLE", { x: 1.95, y: 1.35, w: 2.0, h: 0.22, fontSize: 9, bold: true, color: C.accent5, charSpacing: 2 });
    T(s, "RESPONSE", { x: 4.05, y: 1.35, w: 1.6, h: 0.22, fontSize: 9, bold: true, color: C.accent5, charSpacing: 2 });
    rows.forEach(([c, col, ex, resp], i) => {
      const y = 1.62 + i * 0.68;
      card(s, 0.5, y, 5.3, 0.6, i % 2 ? C.background1 : C.background2, "Cause row");
      chip(s, c, 0.6, y + 0.13, 1.25, 0.34, col, col === HEX.gray || col === HEX.sage || col === HEX.amber ? HEX.ink : HEX.white, { fontSize: 10 });
      T(s, ex, { x: 1.95, y, w: 2.0, h: 0.6, fontSize: 10.5, valign: "middle" });
      T(s, resp, { x: 4.05, y, w: 1.7, h: 0.6, fontSize: 10.5, bold: true, color: C.text2, valign: "middle" });
    });
    T(s, "RETESTED: ONLY THE SERVER CHANGED", { x: 6.1, y: 1.35, w: 3.4, h: 0.22, fontSize: 9, bold: true, color: C.accent1, charSpacing: 2 });
    const ba = [
      ["Llama 3.3 70B, adversarial", "0", "4 of 6"],
      ["Claude Opus 5.5, adversarial", "5", "6 of 6"],
      ["GPT-OSS 120B, of 24", "10, 8, 11", "12, 12"],
      ["Burst of 45 calls, answered", "0", "29"],
      ["Durham facility page size", "", "42% smaller"],
    ];
    ba.forEach(([l, b, a], i) => {
      const y = 1.62 + i * 0.68;
      card(s, 6.1, y, 3.4, 0.6, C.background2, "Before after row");
      T(s, l, { x: 6.25, y: y + 0.04, w: 3.1, h: 0.24, fontSize: 10, color: C.accent5 });
      T(s, b ? [{ text: b, options: { color: C.accent5 } }, { text: "   →   ", options: { color: C.accent1, bold: true } }, { text: a, options: { bold: true, color: C.text1 } }] : [{ text: a, options: { bold: true, color: C.text1 } }],
        { x: 6.25, y: y + 0.27, w: 3.1, h: 0.3, fontSize: 13 });
    });
    T(s, "Not blind: the adversarial questions and their fixes were written the same night.", { x: 0.5, y: 5.05 - 0.05, w: 9, h: 0.2, fontSize: 9, italic: true, color: C.accent5 });
  }

  // ===== 17. Security =====
  {
    const s = newSlide("CONTENT", "SECURITY", "Public data, handled with care", "Security and lessons");
    T(s, "OIG's published record, with no CUI. Findings are addressed to roles and offices; the server never guesses who was responsible.", { x: 0.5, y: 1.32, w: 9, h: 0.35, fontSize: 12, italic: true, color: C.text2 });
    const tiles = [
      ["LuLock", "MCP endpoint", "Bearer token compared in constant time; per-client rate limit; Host and Origin checks", "22 deployment checks"],
      ["LuFilter", "Tool input", "Typed and bounded; traversal, injection, and search syntax refused cleanly", "49 robustness checks"],
      ["LuRoute", "Outbound requests", "One fixed origin; no redirects or proxies; bounded responses; at most eight at once", "Automated tests"],
      ["LuQuote", "Prompt injection", "Report text marked as quotation; read-only tools; scope in the server's instructions", "6 adversarial questions"],
      ["LuKeyRound", "Secrets", "From the environment or an Orchestrate connection; never in results, logs, or the image", "15 image checks, history scan"],
      ["LuPackageCheck", "Container and supply chain", "Non-root, read-only filesystem; locked, audited dependencies; pinned image and actions", "CI and Dependabot"],
    ];
    for (const [k, t] of tiles.entries()) {
      const x = 0.5 + (k % 3) * 3.05, y = 1.78 + Math.floor(k / 3) * 1.6;
      card(s, x, y, 2.9, 1.48, C.background2, "Security tile");
      await iconDot(s, t[0], x + 0.15, y + 0.15, 0.42, HEX.teal, HEX.white, "Security icon");
      T(s, t[1], { x: x + 0.67, y: y + 0.15, w: 2.1, h: 0.42, fontSize: 12.5, bold: true, valign: "middle" });
      T(s, t[2], { x: x + 0.15, y: y + 0.63, w: 2.6, h: 0.52, fontSize: 9.5 });
      T(s, t[3], { x: x + 0.15, y: y + 1.15, w: 2.6, h: 0.25, fontSize: 9.5, bold: true, color: C.accent1 });
    }
    T(s, "Independent review, November 17: no high-severity issues; medium and low findings fixed, each with a test.", { x: 0.5, y: 4.98, w: 8.4, h: 0.2, fontSize: 9.5, italic: true, color: C.accent5 });
  }

  // ===== 18. Lessons =====
  {
    const s = newSlide("CONTENT_DARK", "LESSONS LEARNED AND RECOMMENDATIONS", "Seven lessons for MCP server builders", "Security and lessons");
    const L = [
      ["Compute gold answers from the source data", "Not from the API under test: SQL on a frozen snapshot caught its errors."],
      ["Test with several models", "The best model at its ceiling hides the gaps a weaker one finds."],
      ["Make an empty result say so", "A filter that matches nothing becomes a confident wrong answer."],
      ["Put guardrails in the server", "Its instructions and results reach every agent that connects."],
      ["Read failures against traces", "Before blaming the server, the model, the platform, or the scorer."],
      ["Give every protocol feature a fallback", "Hosts support MCP unevenly. Then test in real hosts."],
      ["Tell the AI what the user decided", "One added line made elicitation work end to end."],
    ];
    L.forEach(([h, b], i) => {
      const col = i < 4 ? 0 : 1, row = i < 4 ? i : i - 4;
      const x = 0.5 + col * 4.6, y = 1.4 + row * 0.9;
      numDot(s, i + 1, x, y + 0.02, 0.44, i === 6 ? HEX.amber : HEX.teal, i === 6 ? HEX.ink : HEX.white);
      T(s, h, { x: x + 0.6, y, w: 3.8, h: 0.3, fontSize: 13, bold: true, color: i === 6 ? C.accent1 : C.background1 });
      T(s, b, { x: x + 0.6, y: y + 0.3, w: 3.8, h: 0.5, fontSize: 11, color: C.accent3 });
    });
    T(s, "github.com/HacksterT/oig-mcp", { x: 5.1, y: 4.55, w: 4.4, h: 0.35, fontSize: 13, bold: true, color: C.accent1, align: "right" });
  }

  fs.mkdirSync(OUT, { recursive: true });
  const file = path.join(OUT, "oig-mcp-deck.pptx");
  await pres.writeFile({ fileName: file });
  await applyTheme(file, THEME);
  console.log(file, cur.n, "slides");
})().catch((e) => { console.error(e); process.exit(1); });
