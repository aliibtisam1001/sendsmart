import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
const workspaceDir = process.cwd();
const SKILL_DIR = process.env.PRESENTATIONS_SKILL_DIR;
const RUNTIME_PYTHON = process.env.RUNTIME_PYTHON;
const RUNTIME_NODE_MODULES = process.env.RUNTIME_NODE_MODULES;
if (!SKILL_DIR || !RUNTIME_PYTHON || !RUNTIME_NODE_MODULES) {
  throw new Error("Set PRESENTATIONS_SKILL_DIR, RUNTIME_PYTHON, and RUNTIME_NODE_MODULES before building.");
}
const artifactToolUrl = pathToFileURL(path.join(RUNTIME_NODE_MODULES, "@oai", "artifact-tool", "dist", "artifact_tool.mjs")).href;
const { Presentation, PresentationFile } = await import(artifactToolUrl);
const buildDir = path.join(workspaceDir, ".slides-build");
const finalPath = path.join(workspaceDir, "output", "SendSmart_Presentation_Final.pptx");
const font = "Aptos";

const C = {
  navy: "#070B24",
  ink: "#111827",
  blue: "#2857D9",
  cyan: "#27C7D8",
  magenta: "#E24B9B",
  violet: "#6D3BD1",
  green: "#18A875",
  amber: "#F59E0B",
  red: "#D83A52",
  white: "#FFFFFF",
  paper: "#F6F7FB",
  muted: "#667085",
  line: "#D9DCE8",
};

function addText(slide, text, left, top, width, height, options = {}) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    position: { left, top, width, height },
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  shape.text = text;
  shape.text.style = {
    typeface: font,
    fontSize: options.fontSize ?? 20,
    bold: options.bold ?? false,
    color: options.color ?? C.ink,
    alignment: options.alignment ?? "left",
    verticalAlignment: options.verticalAlignment ?? "middle",
  };
  return shape;
}

function addBox(slide, left, top, width, height, fill, radius = "rounded-lg", line = "none") {
  return slide.shapes.add({
    geometry: radius === "none" ? "rect" : "roundRect",
    position: { left, top, width, height },
    fill,
    line: { style: "solid", fill: line, width: line === "none" ? 0 : 1 },
    ...(radius === "none" ? {} : { borderRadius: radius }),
  });
}

function addTitle(slide, number, title, subtitle = "") {
  addText(slide, String(number).padStart(2, "0"), 64, 42, 52, 28, { fontSize: 13, bold: true, color: C.magenta });
  addText(slide, title, 64, 76, 1020, 56, { fontSize: 34, bold: true, color: C.ink });
  if (subtitle) addText(slide, subtitle, 64, 132, 1080, 40, { fontSize: 17, color: C.muted });
  addBox(slide, 64, 688, 1152, 2, C.line, "none");
  addText(slide, "SendSmart · SANDBOX / MOCK DATA", 64, 692, 420, 18, { fontSize: 10, color: C.muted });
}

function addMetric(slide, value, label, left, top, color = C.blue) {
  addText(slide, value, left, top, 230, 70, { fontSize: 48, bold: true, color });
  addText(slide, label, left, top + 70, 245, 48, { fontSize: 17, color: C.muted });
}

function addBand(slide, y, color, label, condition, action) {
  addBox(slide, 90, y, 1100, 104, C.white, "rounded-lg", C.line);
  addBox(slide, 90, y, 18, 104, color, "none");
  addText(slide, label, 132, y + 16, 190, 36, { fontSize: 25, bold: true, color });
  addText(slide, condition, 335, y + 14, 515, 72, { fontSize: 17, color: C.ink });
  addText(slide, action, 870, y + 14, 280, 72, { fontSize: 16, bold: true, color: C.ink });
}

async function addCoverImage(slide) {
  const imagePath = path.join(workspaceDir, "slides", "assets", "fintechathon-cover.png");
  const bytes = await fs.readFile(imagePath);
  slide.images.add({
    blob: bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength),
    contentType: "image/png",
    alt: "2026 Shenzhen International FinTechathon cover artwork",
    fit: "cover",
    position: { left: 760, top: 0, width: 520, height: 720 },
  });
}

async function main() {
  await fs.mkdir(buildDir, { recursive: true });
  await fs.mkdir(path.dirname(finalPath), { recursive: true });
  const deck = Presentation.create({ slideSize: { width: 1280, height: 720 } });

  // 1. Cover
  {
    const slide = deck.slides.add();
    slide.background.fill = C.navy;
    await addCoverImage(slide);
    addBox(slide, 0, 0, 830, 720, C.navy, "none");
    addText(slide, "SENDSMART", 72, 82, 540, 36, { fontSize: 15, bold: true, color: C.cyan });
    addText(slide, "Cross-border student payments with code-held authority", 72, 145, 610, 190, { fontSize: 46, bold: true, color: C.white });
    addText(slide, "The agent understands and explains. Deterministic policy decides whether a simulated payment may execute.", 72, 362, 560, 104, { fontSize: 22, color: "#D8DDF5" });
    addText(slide, "2026 Shenzhen International FinTechathon · Topic C", 72, 614, 600, 34, { fontSize: 16, color: C.white });
    addText(slide, "SANDBOX · MOCK DATA · NO REAL FUNDS", 72, 654, 600, 26, { fontSize: 12, bold: true, color: C.magenta });
  }

  // 2. Problem
  {
    const slide = deck.slides.add(); slide.background.fill = C.paper;
    addTitle(slide, 2, "A high-consequence task with fragmented information", "An international student must balance total cost, arrival time, and payment safety.");
    addText(slide, "Aisha", 76, 210, 210, 40, { fontSize: 28, bold: true, color: C.violet });
    addText(slide, "Malaysia to the UK\nGBP 9,000 tuition target\nFive-day deadline", 76, 260, 260, 122, { fontSize: 20, color: C.ink });
    addBox(slide, 370, 230, 2, 300, C.line, "none");
    const items = [
      ["Opaque quotes", "Fees and FX markup appear in different places."],
      ["Deadline risk", "The cheapest route may arrive after tuition is due."],
      ["Account fraud", "A changed bank fingerprint can redirect payment."],
      ["Weak control", "A conversational answer must never equal authorization."],
    ];
    items.forEach((item, i) => {
      const y = 202 + i * 105;
      addText(slide, String(i + 1), 420, y, 54, 54, { fontSize: 28, bold: true, color: i === 3 ? C.red : C.blue, alignment: "center" });
      addText(slide, item[0], 500, y, 250, 30, { fontSize: 21, bold: true });
      addText(slide, item[1], 500, y + 32, 580, 48, { fontSize: 17, color: C.muted });
    });
  }

  // 3. Capabilities
  {
    const slide = deck.slides.add(); slide.background.fill = C.white;
    addTitle(slide, 3, "Five capabilities in one visible flow");
    const labels = [
      ["Understand", "Classify intent, extract slots, ask one question"],
      ["Plan", "Show ordered steps before any execution"],
      ["Protect", "Apply tiers, guardrails, tokens, and audit"],
      ["Control", "Approve, edit, reject, cancel, or stop"],
      ["Measure", "Report savings, risk avoided, and accuracy"],
    ];
    labels.forEach((item, i) => {
      const x = 68 + i * 236;
      addText(slide, String(i + 1), x, 220, 70, 70, { fontSize: 50, bold: true, color: [C.blue,C.violet,C.red,C.magenta,C.green][i] });
      addText(slide, item[0], x, 308, 205, 42, { fontSize: 24, bold: true });
      addText(slide, item[1], x, 360, 198, 118, { fontSize: 17, color: C.muted });
      if (i < 4) addBox(slide, x + 212, 223, 2, 260, C.line, "none");
    });
    addText(slide, "The complete flow works without an API key or network connection.", 68, 565, 1050, 48, { fontSize: 24, bold: true, color: C.ink });
  }

  // 4. Architecture
  {
    const slide = deck.slides.add(); slide.background.fill = C.paper;
    addTitle(slide, 4, "A narrow authorization boundary", "Language understanding can propose actions. It cannot authorize them.");
    const xs = [58, 280, 502, 724, 946];
    const blocks = [
      ["Untrusted input", "Chat and invoice text", C.muted],
      ["Reasoning", "Intent, parser, plan, ranking", C.blue],
      ["Policy", "Hard rules and permission tier", C.red],
      ["User checkpoint", "Confirm or exact typed approval", C.magenta],
      ["Sandbox", "One-time token and receipt", C.green],
    ];
    blocks.forEach((b, i) => {
      addBox(slide, xs[i], 260, 180, 170, C.white, "rounded-lg", C.line);
      addBox(slide, xs[i], 260, 180, 10, b[2], "none");
      addText(slide, b[0], xs[i] + 16, 292, 148, 54, { fontSize: 21, bold: true, color: b[2] });
      addText(slide, b[1], xs[i] + 16, 350, 148, 66, { fontSize: 16, color: C.ink });
      if (i < 4) addBox(slide, xs[i] + 180, 341, 42, 3, C.line, "none");
    });
    addBox(slide, 280, 506, 846, 78, "#EBEEFA", "rounded-lg", C.line);
    addText(slide, "Hash-chained audit", 310, 521, 220, 46, { fontSize: 21, bold: true, color: C.violet });
    addText(slide, "Plan transitions, policy decisions, approvals, receipts, cancellation, and STOP AGENT events", 530, 519, 560, 50, { fontSize: 16, color: C.ink });
  }

  // 5. Tiers
  {
    const slide = deck.slides.add(); slide.background.fill = C.paper;
    addTitle(slide, 5, "Permission tiers enforced by deterministic code");
    addBand(slide, 186, C.blue, "T1 ADVISE", "Comparison only. No execution steps exist in the plan.", "Review recommendation");
    addBand(slide, 302, C.green, "T2 CONFIRM", "Verified beneficiary and no more than USD 500 equivalent.", "Click Confirm");
    addBand(slide, 418, C.amber, "T3 APPROVE", "Verified beneficiary, above USD 500 through USD 10,000.", "Type exact phrase");
    addBand(slide, 534, C.red, "BLOCKED", "Any hard guardrail fires. The policy engine cannot mint a token.", "Resolve condition");
  }

  // 6. Security
  {
    const slide = deck.slides.add(); slide.background.fill = C.white;
    addTitle(slide, 6, "Security controls survive a compromised model");
    const left = [
      ["Invoice injection", "Instruction-like document text is data and triggers a block."],
      ["Account change", "A bank fingerprint mismatch blocks redirection."],
      ["Amount and daily caps", "Policy calculates USD equivalent with Decimal math."],
    ];
    const right = [
      ["Forged or replayed token", "The sandbox verifies HMAC, binding, expiry, and single use."],
      ["Audit editing", "Hash-chain verification fails after any event mutation."],
      ["STOP AGENT", "The executor checks the kill switch before token handling."],
    ];
    [left, right].forEach((column, c) => column.forEach((item, i) => {
      const x = c === 0 ? 72 : 674; const y = 205 + i * 145;
      addBox(slide, x, y, 520, 3, c === 0 ? C.red : C.violet, "none");
      addText(slide, item[0], x, y + 18, 500, 36, { fontSize: 22, bold: true });
      addText(slide, item[1], x, y + 58, 490, 64, { fontSize: 17, color: C.muted });
    }));
  }

  // 7. Control
  {
    const slide = deck.slides.add(); slide.background.fill = C.paper;
    addTitle(slide, 7, "The user remains in control at every decision point");
    const stages = [
      ["Plan", "Inspect every ordered step"],
      ["Edit", "Change priority or route"],
      ["Approve", "Confirm or type exact phrase"],
      ["Hold", "Cancel while payment is pending"],
      ["Stop", "Kill switch overrides all action"],
    ];
    stages.forEach((item, i) => {
      const x = 66 + i * 238;
      addBox(slide, x, 230, 194, 210, C.white, "rounded-lg", C.line);
      addText(slide, String(i + 1), x + 18, 248, 56, 52, { fontSize: 38, bold: true, color: [C.blue,C.violet,C.green,C.amber,C.red][i] });
      addText(slide, item[0], x + 18, 310, 156, 34, { fontSize: 24, bold: true });
      addText(slide, item[1], x + 18, 354, 156, 72, { fontSize: 16, color: C.muted });
    });
    addText(slide, "Preferences may tighten a limit. They can never raise the USD 10,000 hard cap.", 68, 530, 1020, 50, { fontSize: 24, bold: true, color: C.ink });
  }

  // 8. Value
  {
    const slide = deck.slides.add(); slide.background.fill = C.white;
    addTitle(slide, 8, "Measured value on mock routes", "GBP 9,000 tuition scenario. Costs shown in MYR from fictional providers.");
    addMetric(slide, "685.22", "MYR computed cost saving versus the mock bank wire", 70, 188, C.green);
    addMetric(slide, "78.70%", "Lower fee plus FX markup versus that baseline", 70, 340, C.blue);
    addMetric(slide, "24 min", "Manual comparison estimate for six providers", 70, 492, C.violet);
    slide.charts.add("bar", {
      position: { left: 430, top: 205, width: 760, height: 395 },
      categories: ["ScholarTransfer", "SwiftFox", "CampusBridge", "GlobalNest", "OrbitRemit", "Bank wire"],
      series: [{ name: "Fee + FX markup (MYR)", values: [185.50, 222.28, 280.44, 301.32, 318.64, 870.72], fill: C.blue }],
      hasLegend: false,
      dataLabels: { showValue: true, position: "outEnd" },
      xAxis: { majorGridlines: { style: "solid", fill: C.line, width: 1 } },
    });
    addText(slide, "All figures use MOCK data. Savings do not predict real provider pricing.", 430, 612, 740, 34, { fontSize: 14, color: C.red });
  }

  // 9. Evidence
  {
    const slide = deck.slides.add(); slide.background.fill = C.paper;
    addTitle(slide, 9, "Reproducible evidence, not a scripted happy path");
    addMetric(slide, "22 / 22", "Executable scenarios passed", 74, 208, C.green);
    addMetric(slide, "30 / 30", "Automated tests passed", 340, 208, C.blue);
    addMetric(slide, "93%", "Measured coverage for non-UI modules", 606, 208, C.violet);
    addMetric(slide, "36", "Intent benchmark utterances", 872, 208, C.magenta);
    addBox(slide, 74, 432, 1110, 3, C.line, "none");
    addText(slide, "Curated benchmark results", 74, 462, 340, 36, { fontSize: 21, bold: true });
    addText(slide, "100% intent accuracy", 74, 514, 300, 34, { fontSize: 19, color: C.ink });
    addText(slide, "100% slot F1", 390, 514, 240, 34, { fontSize: 19, color: C.ink });
    addText(slide, "100% clarification correctness", 650, 514, 360, 34, { fontSize: 19, color: C.ink });
    addText(slide, "These results describe the included curated datasets only.", 74, 578, 780, 34, { fontSize: 15, color: C.red });
  }

  // 10. Close
  {
    const slide = deck.slides.add(); slide.background.fill = C.navy;
    addText(slide, "SENDSMART", 72, 70, 320, 34, { fontSize: 15, bold: true, color: C.cyan });
    addText(slide, "A financial agent that earns trust by giving up authority", 72, 132, 1030, 118, { fontSize: 44, bold: true, color: C.white });
    addText(slide, "Working now", 72, 312, 240, 32, { fontSize: 22, bold: true, color: C.green });
    addText(slide, "Offline fallback, visible plans, deterministic policy, user checkpoints, simulated receipts, and evidence generation", 72, 354, 510, 118, { fontSize: 18, color: "#D8DDF5" });
    addText(slide, "Honest limits", 666, 312, 240, 32, { fontSize: 22, bold: true, color: C.magenta });
    addText(slide, "No real payment rail, KYC/AML system, market pricing, or production-grade injection defense", 666, 354, 470, 100, { fontSize: 18, color: "#D8DDF5" });
    addText(slide, "Next step: connect regulated providers while preserving the same authorization boundary.", 72, 570, 1050, 54, { fontSize: 24, bold: true, color: C.white });
    addText(slide, "SANDBOX · MOCK DATA · NO REAL FUNDS", 72, 657, 500, 24, { fontSize: 12, bold: true, color: C.magenta });
  }

  for (let i = 0; i < deck.slides.items.length; i++) {
    const slide = deck.slides.items[i];
    const png = await deck.export({ slide, format: "png", scale: 1 });
    await fs.writeFile(path.join(buildDir, `slide-${String(i + 1).padStart(2, "0")}.png`), new Uint8Array(await png.arrayBuffer()));
  }
  const montage = await deck.export({ format: "webp", montage: true });
  await fs.writeFile(path.join(buildDir, "montage.webp"), new Uint8Array(await montage.arrayBuffer()));

  const { finalizePresentation } = await import(pathToFileURL(path.join(SKILL_DIR, "container_tools/artifact_tool_utils.mjs")).href);
  const candidatePath = path.join(buildDir, "candidate.pptx");
  await (await PresentationFile.exportPptx(deck)).save(candidatePath);
  await finalizePresentation({
    workspaceDir,
    candidatePath,
    finalPath,
    pythonExecutable: RUNTIME_PYTHON,
    integrityValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_package_integrity.py"),
    layoutValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_layout_geometry.py"),
    layoutArgs: ["--expected-slide-size-emu", "12192000,6858000", "--validate-heading-fit"],
    explicitTotalSlideCount: 10,
    requiredNativeTableOwnerSlides: [],
    requiredNativeChartOwnerSlides: [8],
    requiredEmbeddedWorkbookChartOwnerSlides: [],
    materializeLiteralChartWorkbooks: true,
    fontPolicy: { basis: "design", families: [font] },
    verifyArtifactToolImport: true,
    receiptPath: path.join(buildDir, "validation-final.json"),
  });
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

