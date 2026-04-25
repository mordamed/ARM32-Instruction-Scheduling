// build_deck.js — Generates the INFO-H410 oral presentation deck.
// Run from /sessions/practical-funny-noether (where pptxgenjs is installed):
//   node mnt/Project/presentation/build_deck.js
//
// Output: mnt/Project/presentation/INFO-H410_presentation.pptx

const path = require("path");
const pptxgen = require("pptxgenjs");

// ---------- Palette : Ocean Gradient (security / crypto vibe) ----------
const NAVY     = "21295C";  // dark sandwich
const DEEP     = "065A82";
const TEAL     = "1C7293";
const PALE     = "F4F7FA";  // light slide background
const INK      = "1B2331";  // body text on light bg
const MUTED    = "5C6B82";
const ACCENT   = "F4A261";  // warm accent (NOPs, warnings)
const SUCCESS  = "2A9D8F";

const FH = "Calibri";       // header
const FB = "Calibri";       // body

// ---------- Helpers ----------
function darkBg(slide) {
  slide.background = { color: NAVY };
}
function lightBg(slide) {
  slide.background = { color: PALE };
}

// Section header strip on light slides
function header(slide, title, subtitle) {
  slide.addShape("rect", { x: 0, y: 0, w: 10, h: 0.7, fill: { color: NAVY }, line: { color: NAVY } });
  slide.addText(title, {
    x: 0.4, y: 0.05, w: 9.2, h: 0.6,
    fontFace: FH, fontSize: 22, bold: true, color: "FFFFFF", valign: "middle", margin: 0,
  });
  if (subtitle) {
    slide.addText(subtitle, {
      x: 0.4, y: 0.05, w: 9.2, h: 0.6,
      fontFace: FB, fontSize: 11, italic: true, color: "CADCFC",
      align: "right", valign: "middle", margin: 0,
    });
  }
}

function footer(slide, pageNum, total) {
  slide.addShape("rect", { x: 0, y: 5.4, w: 10, h: 0.225, fill: { color: NAVY }, line: { color: NAVY } });
  slide.addText("INFO-H410 · Side-Channel-Secure ARM32 Scheduling · Mohamed Tajani",
    { x: 0.3, y: 5.4, w: 7, h: 0.225, fontFace: FB, fontSize: 9, color: "CADCFC", valign: "middle", margin: 0 });
  slide.addText(`${pageNum} / ${total}`,
    { x: 8.5, y: 5.4, w: 1.2, h: 0.225, fontFace: FB, fontSize: 9, color: "CADCFC", valign: "middle", align: "right", margin: 0 });
}

// =====================================================================
const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";  // 10 × 5.625 inches
pres.author = "Mohamed Tajani";
pres.company = "Université Libre de Bruxelles";
pres.title = "Side-Channel-Secure ARM32 Instruction Scheduling";

const TOTAL = 12;

// =====================================================================
// SLIDE 1 — Title (dark)
// =====================================================================
{
  const s = pres.addSlide();
  darkBg(s);
  // Decorative accent bar
  s.addShape("rect", { x: 0, y: 2.2, w: 10, h: 0.04, fill: { color: ACCENT }, line: { color: ACCENT } });

  s.addText("Side-Channel-Secure", {
    x: 0.6, y: 1.0, w: 8.8, h: 0.7, fontFace: FH, fontSize: 36, bold: true, color: "FFFFFF", margin: 0,
  });
  s.addText("ARM32 Instruction Scheduling", {
    x: 0.6, y: 1.55, w: 8.8, h: 0.6, fontFace: FH, fontSize: 32, bold: true, color: "FFFFFF", margin: 0,
  });
  s.addText("A comparative study of Bayesian inference, CSP, and Reinforcement Learning",
    { x: 0.6, y: 2.4, w: 8.8, h: 0.5, fontFace: FB, fontSize: 16, italic: true, color: "CADCFC", margin: 0 });

  s.addText([
    { text: "Mohamed Tajani", options: { bold: true, color: "FFFFFF", fontSize: 14, breakLine: true } },
    { text: "INFO-H410 — Artificial Intelligence",     options: { color: "CADCFC", fontSize: 12, breakLine: true } },
    { text: "Université Libre de Bruxelles · 2025-2026", options: { color: "CADCFC", fontSize: 12 } },
  ], { x: 0.6, y: 4.3, w: 8.8, h: 1.1, fontFace: FB, margin: 0 });
}

// =====================================================================
// SLIDE 2 — The Problem
// =====================================================================
{
  const s = pres.addSlide();
  lightBg(s);
  header(s, "The problem", "Why naïve scheduling leaks your secret");

  // Left column: text
  s.addText([
    { text: "Boolean masking splits a secret:", options: { bold: true, color: INK, fontSize: 14, breakLine: true } },
    { text: " ", options: { breakLine: true, fontSize: 6 } },
    { text: "s = A ⊕ B", options: { bold: true, color: DEEP, fontSize: 22, breakLine: true } },
    { text: " ", options: { breakLine: true, fontSize: 6 } },
    { text: "On an in-order pipeline (Cortex-M3/M4), if instructions on share A and share B are issued within k cycles, the register file holds both intermediates simultaneously.",
      options: { color: INK, fontSize: 13, breakLine: true } },
    { text: " ", options: { breakLine: true, fontSize: 6 } },
    { text: "→ Hamming-distance leakage in the power trace. First-order resistance broken.",
      options: { color: ACCENT, fontSize: 13, italic: true, bold: true } },
  ], { x: 0.4, y: 1.0, w: 5.3, h: 4.0, fontFace: FB, margin: 0, valign: "top" });

  // Right column: schematic
  // Pipeline timeline
  s.addShape("rect", { x: 6.0, y: 1.2, w: 3.6, h: 1.6, fill: { color: "FFFFFF" }, line: { color: TEAL, width: 1 } });
  s.addText("Pipeline (k = 3)", { x: 6.0, y: 1.2, w: 3.6, h: 0.35, fontFace: FB, fontSize: 11, bold: true, color: TEAL, align: "center", margin: 0 });

  // Cycle blocks
  const cycles = [
    { label: "A", color: DEEP },
    { label: "B", color: ACCENT },
    { label: "·", color: MUTED },
    { label: "·", color: MUTED },
    { label: "A", color: DEEP },
    { label: "B", color: ACCENT },
  ];
  cycles.forEach((c, i) => {
    s.addShape("rect", {
      x: 6.1 + i * 0.55, y: 1.7, w: 0.5, h: 0.5,
      fill: { color: c.color }, line: { color: c.color },
    });
    s.addText(c.label, {
      x: 6.1 + i * 0.55, y: 1.7, w: 0.5, h: 0.5,
      fontFace: FH, fontSize: 14, bold: true, color: "FFFFFF",
      align: "center", valign: "middle", margin: 0,
    });
  });

  // Arrow showing leakage
  s.addText("⚡ leakage", { x: 6.0, y: 2.35, w: 1.4, h: 0.3, fontFace: FB, fontSize: 11, bold: true, color: ACCENT, margin: 0 });
  s.addText("safe (Δt ≥ k)", { x: 8.3, y: 2.35, w: 1.4, h: 0.3, fontFace: FB, fontSize: 11, color: SUCCESS, margin: 0 });

  // Bottom: real-world note
  s.addShape("rect", { x: 6.0, y: 3.3, w: 3.6, h: 1.7, fill: { color: "E8EEF4" }, line: { color: "E8EEF4" } });
  s.addText([
    { text: "Real-world impact", options: { bold: true, color: NAVY, fontSize: 12, breakLine: true } },
    { text: " ", options: { breakLine: true, fontSize: 4 } },
    { text: "Power-analysis attacks on naïvely-compiled masked AES recover full keys in minutes (Kocher 1999, and 25 years of follow-up).",
      options: { color: INK, fontSize: 11, italic: true } },
  ], { x: 6.15, y: 3.4, w: 3.4, h: 1.5, fontFace: FB, margin: 0, valign: "top" });

  footer(s, 2, TOTAL);
}

// =====================================================================
// SLIDE 3 — Formal Problem
// =====================================================================
{
  const s = pres.addSlide();
  lightBg(s);
  header(s, "Formal problem", "Scheduling as constrained optimisation");

  s.addText("Given a basic block I = {I₀, …, I_{n-1}}, assign a start cycle tᵢ to every instruction.",
    { x: 0.4, y: 1.0, w: 9.2, h: 0.45, fontFace: FB, fontSize: 14, color: INK, margin: 0 });

  // Three constraint cards
  const cards = [
    {
      title: "RAW",
      sub: "Read-After-Write",
      formula: "t_j ≥ tᵢ + ℓᵢ",
      desc: "If j depends on i, j cannot start before i finishes (ℓ = latency).",
      color: DEEP,
    },
    {
      title: "SEC",
      sub: "Security distance",
      formula: "|tᵢ − t_j| ≥ k",
      desc: "Different shares (A vs B) must be separated by at least k cycles.",
      color: ACCENT,
    },
    {
      title: "SLOT",
      sub: "One per cycle",
      formula: "tᵢ ≠ t_j",
      desc: "In-order, single-issue pipeline: one instruction per cycle.",
      color: TEAL,
    },
  ];

  cards.forEach((c, i) => {
    const x = 0.4 + i * 3.15;
    s.addShape("rect", { x, y: 1.6, w: 3.0, h: 2.5, fill: { color: "FFFFFF" }, line: { color: "DCE3EE", width: 1 } });
    s.addShape("rect", { x, y: 1.6, w: 3.0, h: 0.45, fill: { color: c.color }, line: { color: c.color } });
    s.addText(c.title, { x: x + 0.15, y: 1.6, w: 1.5, h: 0.45, fontFace: FH, fontSize: 16, bold: true, color: "FFFFFF", valign: "middle", margin: 0 });
    s.addText(c.sub,   { x: x + 1.5,  y: 1.6, w: 1.4, h: 0.45, fontFace: FB, fontSize: 10, italic: true, color: "FFFFFF", valign: "middle", align: "right", margin: 0 });
    s.addText(c.formula, { x: x + 0.15, y: 2.15, w: 2.7, h: 0.55, fontFace: "Cambria", fontSize: 18, bold: true, color: c.color, align: "center", valign: "middle", margin: 0 });
    s.addText(c.desc,   { x: x + 0.15, y: 2.85, w: 2.7, h: 1.15, fontFace: FB, fontSize: 11, color: INK, valign: "top", margin: 0 });
  });

  // Objective box
  s.addShape("rect", { x: 0.4, y: 4.3, w: 9.2, h: 0.85, fill: { color: NAVY }, line: { color: NAVY } });
  s.addText([
    { text: "Objective: ", options: { bold: true, color: ACCENT, fontSize: 14 } },
    { text: "minimise the makespan ", options: { color: "FFFFFF", fontSize: 14 } },
    { text: "max(tᵢ + ℓᵢ) ", options: { fontFace: "Cambria", italic: true, color: "FFFFFF", fontSize: 15 } },
    { text: "— equivalently, minimise the number of inserted NOPs.", options: { color: "CADCFC", fontSize: 13, italic: true } },
  ], { x: 0.6, y: 4.3, w: 8.8, h: 0.85, fontFace: FB, valign: "middle", margin: 0 });

  footer(s, 3, TOTAL);
}

// =====================================================================
// SLIDE 4 — Why three AI techniques?
// =====================================================================
{
  const s = pres.addSlide();
  lightBg(s);
  header(s, "Why three AI techniques?", "Three paradigms, one problem");

  s.addText("The problem is NP-hard but its structure maps naturally to three different paradigms covered in INFO-H410:",
    { x: 0.4, y: 1.0, w: 9.2, h: 0.6, fontFace: FB, fontSize: 13, color: INK, italic: true, margin: 0 });

  const techs = [
    { tag: "A", title: "Bayesian network", paradigm: "Probabilistic inference", trait: "soft, continuous risk", color: DEEP },
    { tag: "B", title: "CSP / CP-SAT", paradigm: "Combinatorial optimisation", trait: "hard, optimal", color: ACCENT },
    { tag: "C", title: "MDP / DQN", paradigm: "Reinforcement learning", trait: "fast inference, learnt policy", color: TEAL },
  ];

  techs.forEach((t, i) => {
    const x = 0.4 + i * 3.15;
    s.addShape("rect", { x, y: 1.85, w: 3.0, h: 3.2, fill: { color: "FFFFFF" }, line: { color: "DCE3EE", width: 1 } });
    // Big tag circle
    s.addShape("ellipse", { x: x + 1.15, y: 2.05, w: 0.7, h: 0.7, fill: { color: t.color }, line: { color: t.color } });
    s.addText(t.tag, { x: x + 1.15, y: 2.05, w: 0.7, h: 0.7, fontFace: FH, fontSize: 26, bold: true, color: "FFFFFF", align: "center", valign: "middle", margin: 0 });
    s.addText(t.title, { x: x + 0.1, y: 2.85, w: 2.8, h: 0.5, fontFace: FH, fontSize: 16, bold: true, color: INK, align: "center", margin: 0 });
    s.addText(t.paradigm, { x: x + 0.1, y: 3.35, w: 2.8, h: 0.4, fontFace: FB, fontSize: 12, italic: true, color: MUTED, align: "center", margin: 0 });
    s.addShape("line", { x: x + 0.5, y: 3.85, w: 2.0, h: 0, line: { color: t.color, width: 1.5 } });
    s.addText(t.trait, { x: x + 0.1, y: 4.0, w: 2.8, h: 0.85, fontFace: FB, fontSize: 13, color: INK, align: "center", valign: "top", margin: 0 });
  });

  footer(s, 4, TOTAL);
}

// =====================================================================
// SLIDE 5 — Approach A: Bayesian
// =====================================================================
{
  const s = pres.addSlide();
  lightBg(s);
  header(s, "Approach A — Bayesian network inference", "Soft probabilistic risk model");

  // Left: explanation
  s.addText([
    { text: "Idea ", options: { bold: true, color: DEEP, fontSize: 14, breakLine: true } },
    { text: "Side-channel leakage is not binary — it decays continuously with Δt.", options: { color: INK, fontSize: 12, breakLine: true } },
    { text: " ", options: { breakLine: true, fontSize: 4 } },
    { text: "Conditional Probability Table ", options: { bold: true, color: DEEP, fontSize: 14, breakLine: true } },
    { text: "Models the pipeline capacitor discharge:", options: { color: INK, fontSize: 12 } },
  ], { x: 0.4, y: 1.0, w: 4.6, h: 1.7, fontFace: FB, margin: 0, valign: "top" });

  // CPT mini-table
  const cpt = [
    [{ text: "Δt (cycles)", options: { bold: true, fill: { color: NAVY }, color: "FFFFFF", align: "center" } },
     { text: "P(L = 1)",   options: { bold: true, fill: { color: NAVY }, color: "FFFFFF", align: "center" } }],
    ["1", "≈ 0.95"],
    ["2", "≈ 0.50"],
    ["3", "≈ 0.10"],
    ["≥ 4", "≈ 0.00"],
  ];
  s.addTable(cpt, {
    x: 0.4, y: 2.7, w: 4.6, h: 1.9,
    fontFace: FB, fontSize: 12, color: INK,
    border: { pt: 0.5, color: "DCE3EE" }, align: "center", valign: "middle",
    colW: [2.3, 2.3],
  });

  // Right: algorithm summary
  s.addShape("rect", { x: 5.3, y: 1.0, w: 4.4, h: 4.0, fill: { color: "FFFFFF" }, line: { color: "DCE3EE", width: 1 } });
  s.addShape("rect", { x: 5.3, y: 1.0, w: 0.08, h: 4.0, fill: { color: DEEP }, line: { color: DEEP } });
  s.addText("Greedy scheduling with risk threshold τ", {
    x: 5.5, y: 1.1, w: 4.1, h: 0.45, fontFace: FH, fontSize: 14, bold: true, color: NAVY, margin: 0,
  });
  s.addText([
    { text: "1. ", options: { bold: true, color: DEEP, fontSize: 12 } },
    { text: "Compute the marginal expected leakage E[L] for every data-ready candidate.", options: { color: INK, fontSize: 12, breakLine: true } },
    { text: " ", options: { breakLine: true, fontSize: 4 } },
    { text: "2. ", options: { bold: true, color: DEEP, fontSize: 12 } },
    { text: "Pick the candidate that minimises E[L].", options: { color: INK, fontSize: 12, breakLine: true } },
    { text: " ", options: { breakLine: true, fontSize: 4 } },
    { text: "3. ", options: { bold: true, color: DEEP, fontSize: 12 } },
    { text: "If even the best E[L] > τ (e.g. 0.15), inject a NOP. Δt grows, risk decays under τ.", options: { color: INK, fontSize: 12, breakLine: true } },
    { text: " ", options: { breakLine: true, fontSize: 4 } },
    { text: "Cost: ", options: { bold: true, color: DEEP, fontSize: 12 } },
    { text: "O(n²) inference, no training.", options: { color: INK, fontSize: 12, italic: true } },
  ], { x: 5.5, y: 1.6, w: 4.1, h: 3.3, fontFace: FB, margin: 0, valign: "top" });

  footer(s, 5, TOTAL);
}

// =====================================================================
// SLIDE 6 — Approach B: CSP
// =====================================================================
{
  const s = pres.addSlide();
  lightBg(s);
  header(s, "Approach B — Constraint Satisfaction (CP-SAT)", "Declarative, optimal");

  // Left card: encoding
  s.addShape("rect", { x: 0.4, y: 1.0, w: 4.6, h: 4.0, fill: { color: "FFFFFF" }, line: { color: "DCE3EE", width: 1 } });
  s.addShape("rect", { x: 0.4, y: 1.0, w: 0.08, h: 4.0, fill: { color: ACCENT }, line: { color: ACCENT } });
  s.addText("Encoding", { x: 0.6, y: 1.1, w: 4.3, h: 0.45, fontFace: FH, fontSize: 14, bold: true, color: NAVY, margin: 0 });
  s.addText([
    { text: "• Integer variables ", options: { color: INK, fontSize: 12 } },
    { text: "tᵢ ∈ [0, T_max]", options: { fontFace: "Cambria", italic: true, color: DEEP, fontSize: 12, breakLine: true } },
    { text: " ", options: { breakLine: true, fontSize: 4 } },
    { text: "• T_max from a greedy warm-start (tight upper bound).", options: { color: INK, fontSize: 12, breakLine: true } },
    { text: " ", options: { breakLine: true, fontSize: 4 } },
    { text: "• SEC encoded as reified disjunction:", options: { color: INK, fontSize: 12, breakLine: true } },
    { text: " ", options: { breakLine: true, fontSize: 4 } },
    { text: "  (t_A − t_B ≥ k) ∨ (t_B − t_A ≥ k)",
      options: { fontFace: "Cambria", italic: true, color: ACCENT, fontSize: 12, breakLine: true } },
    { text: " ", options: { breakLine: true, fontSize: 4 } },
    { text: "• Objective: minimise max(tᵢ + ℓᵢ).", options: { color: INK, fontSize: 12 } },
  ], { x: 0.6, y: 1.6, w: 4.3, h: 3.3, fontFace: FB, margin: 0, valign: "top" });

  // Right card: backend
  s.addShape("rect", { x: 5.3, y: 1.0, w: 4.4, h: 4.0, fill: { color: "FFFFFF" }, line: { color: "DCE3EE", width: 1 } });
  s.addShape("rect", { x: 5.3, y: 1.0, w: 0.08, h: 4.0, fill: { color: ACCENT }, line: { color: ACCENT } });
  s.addText("Solver: Google OR-Tools CP-SAT", {
    x: 5.5, y: 1.1, w: 4.1, h: 0.45, fontFace: FH, fontSize: 14, bold: true, color: NAVY, margin: 0,
  });
  s.addText([
    { text: "• SAT-based propagation + clause learning (CDCL).", options: { color: INK, fontSize: 12, breakLine: true } },
    { text: " ", options: { breakLine: true, fontSize: 4 } },
    { text: "• 4 parallel workers, free multi-core speed-up.", options: { color: INK, fontSize: 12, breakLine: true } },
    { text: " ", options: { breakLine: true, fontSize: 4 } },
    { text: "• Proven optimal for n = 10 in tens of ms.", options: { color: INK, fontSize: 12, breakLine: true } },
    { text: " ", options: { breakLine: true, fontSize: 4 } },
    { text: "• Best-effort under timeout (15 s) for n ≥ 30.", options: { color: INK, fontSize: 12, breakLine: true } },
    { text: " ", options: { breakLine: true, fontSize: 4 } },
    { text: "Fallback: ", options: { bold: true, color: ACCENT, fontSize: 12 } },
    { text: "python-constraint backtracking when OR-Tools is missing (limited to n ≤ 15).",
      options: { color: INK, fontSize: 12, italic: true } },
  ], { x: 5.5, y: 1.6, w: 4.1, h: 3.3, fontFace: FB, margin: 0, valign: "top" });

  footer(s, 6, TOTAL);
}

// =====================================================================
// SLIDE 7 — Approach C: MDP / DQN (in progress)
// =====================================================================
{
  const s = pres.addSlide();
  lightBg(s);
  header(s, "Approach C — MDP / Deep Q-Network", "Learning a scheduling policy via reward shaping");

  // Left: formulation
  s.addText("Markov Decision Process formulation", {
    x: 0.4, y: 1.0, w: 4.8, h: 0.4, fontFace: FH, fontSize: 14, bold: true, color: TEAL, margin: 0,
  });
  s.addText([
    { text: "State ", options: { bold: true, color: NAVY, fontSize: 12 } },
    { text: "6-D feature vector (block-size invariant): ratios of remaining work, distance to last A/B, ready-queue size, critical path.",
      options: { color: INK, fontSize: 12, breakLine: true } },
    { text: " ", options: { breakLine: true, fontSize: 4 } },
    { text: "Action ", options: { bold: true, color: NAVY, fontSize: 12 } },
    { text: "Pick a ready instruction or insert NOP.", options: { color: INK, fontSize: 12, breakLine: true } },
    { text: " ", options: { breakLine: true, fontSize: 4 } },
    { text: "Reward ", options: { bold: true, color: NAVY, fontSize: 12 } },
    { text: "−1 / cycle, ", options: { color: INK, fontSize: 12 } },
    { text: "−100", options: { bold: true, color: ACCENT, fontSize: 12 } },
    { text: " / violation (rescaled), +50 on completion.", options: { color: INK, fontSize: 12 } },
  ], { x: 0.4, y: 1.4, w: 4.8, h: 3.0, fontFace: FB, margin: 0, valign: "top" });

  // Right: training stack
  s.addShape("rect", { x: 5.4, y: 1.0, w: 4.3, h: 3.5, fill: { color: "FFFFFF" }, line: { color: "DCE3EE", width: 1 } });
  s.addShape("rect", { x: 5.4, y: 1.0, w: 0.08, h: 3.5, fill: { color: TEAL }, line: { color: TEAL } });
  s.addText("Training stack", { x: 5.6, y: 1.1, w: 4.0, h: 0.4, fontFace: FH, fontSize: 14, bold: true, color: NAVY, margin: 0 });
  s.addText([
    { text: "• MLP Q(s, a) on PyTorch (GPU when available).", options: { color: INK, fontSize: 12, breakLine: true } },
    { text: " ", options: { breakLine: true, fontSize: 4 } },
    { text: "• Experience replay (10 000), target net every 200 steps.", options: { color: INK, fontSize: 12, breakLine: true } },
    { text: " ", options: { breakLine: true, fontSize: 4 } },
    { text: "• ε-greedy: 1.0 → 0.05, decay 0.997.", options: { color: INK, fontSize: 12, breakLine: true } },
    { text: " ", options: { breakLine: true, fontSize: 4 } },
    { text: "• Huber loss, gradient clipping.", options: { color: INK, fontSize: 12 } },
  ], { x: 5.6, y: 1.55, w: 4.0, h: 2.9, fontFace: FB, margin: 0, valign: "top" });

  // Reward-shaping ablation result
  s.addShape("rect", { x: 0.4, y: 4.55, w: 9.2, h: 0.6, fill: { color: NAVY }, line: { color: NAVY } });
  s.addText([
    { text: "✓ Reward-shaping ablation ", options: { bold: true, color: ACCENT, fontSize: 13 } },
    { text: "(n = 10): rescaling −10 → −100 restores 100 % valid schedules within 6 % of the CSP optimum.",
      options: { color: "FFFFFF", fontSize: 12, italic: true } },
  ], { x: 0.6, y: 4.55, w: 9.0, h: 0.6, fontFace: FB, valign: "middle", margin: 0 });

  footer(s, 7, TOTAL);
}

// =====================================================================
// SLIDE 8 — Experimental setup
// =====================================================================
{
  const s = pres.addSlide();
  lightBg(s);
  header(s, "Experimental setup", "Same blocks, fair comparison");

  const tiles = [
    { num: "n ∈ {10, 30, 50}", label: "Block sizes" },
    { num: "k = 3",              label: "Security distance" },
    { num: "3 seeds",            label: "42 / 43 / 44" },
    { num: "1 toolchain",        label: "Identical block per (n, seed)" },
  ];
  tiles.forEach((t, i) => {
    const x = 0.4 + i * 2.4;
    s.addShape("rect", { x, y: 1.3, w: 2.25, h: 1.6, fill: { color: "FFFFFF" }, line: { color: "DCE3EE", width: 1 } });
    s.addShape("rect", { x, y: 1.3, w: 2.25, h: 0.08, fill: { color: DEEP }, line: { color: DEEP } });
    s.addText(t.num,   { x: x + 0.1, y: 1.45, w: 2.05, h: 0.7, fontFace: FH, fontSize: 18, bold: true, color: NAVY, align: "center", valign: "middle", margin: 0 });
    s.addText(t.label, { x: x + 0.1, y: 2.2, w: 2.05, h: 0.55, fontFace: FB, fontSize: 11, italic: true, color: MUTED, align: "center", valign: "top", margin: 0 });
  });

  s.addText("Metrics reported", {
    x: 0.4, y: 3.2, w: 9.2, h: 0.4, fontFace: FH, fontSize: 14, bold: true, color: NAVY, margin: 0,
  });
  s.addText([
    { text: "• Makespan (total cycles) ", options: { color: INK, fontSize: 12, breakLine: true } },
    { text: "• Number of inserted NOPs ", options: { color: INK, fontSize: 12, breakLine: true } },
    { text: "• Expected leakage E[L] = Σ P(L=1) over all share-AB pairs ", options: { color: INK, fontSize: 12, breakLine: true } },
    { text: "• Wall-clock solver time (training time reported separately for the MDP)", options: { color: INK, fontSize: 12 } },
  ], { x: 0.5, y: 3.65, w: 9.0, h: 1.5, fontFace: FB, margin: 0, valign: "top" });

  footer(s, 8, TOTAL);
}

// =====================================================================
// SLIDE 9 — Results (Bayesian vs CSP)
// =====================================================================
{
  const s = pres.addSlide();
  lightBg(s);
  header(s, "Results at k = 3", "Mean over 3 seeds — MDP † default reward, MDP ★ tuned reward (−100)");

  // Table — use INK for body text, accent only for the method label
  const head = (txt) => ({ text: txt, options: { bold: true, fill: { color: NAVY }, color: "FFFFFF", align: "center" } });
  const rowB = (txt, bold = false) => ({ text: txt, options: { color: INK, bold,  align: "center" } });
  const rowC = (txt, bold = false) => ({ text: txt, options: { color: INK, bold,  align: "center" } });
  const tagB = (txt) => ({ text: txt, options: { color: DEEP,    bold: true, align: "center" } });
  const tagC = (txt) => ({ text: txt, options: { color: "B45A1F", bold: true, align: "center" } });
  const tagM = (txt) => ({ text: txt, options: { color: TEAL,    bold: true, align: "center" } });
  const tagF = (txt) => ({ text: txt, options: { color: "C0392B", bold: true, align: "center" } });
  const tagS = (txt) => ({ text: txt, options: { color: "2A9D8F", bold: true, align: "center" } });
  const data = [
    [head("n"), head("Method"), head("Cycles"), head("NOPs"), head("E[L]"), head("Valid")],
    [{ text: "10", options: { rowspan: 4, valign: "middle", bold: true, align: "center" } }, tagB("Bayesian"), rowB("11.0"),       rowB("1.0"),       rowB("0.05"),       tagS("100 %")],
    [                                                                                        tagC("CSP"),      rowC("11.0", true), rowC("1.0"),       rowC("0.03", true), tagS("100 %")],
    [                                                                                        tagM("MDP †"),    rowB("10.3"),       rowB("0.3"),       rowB("1.40"),       tagF("0 %")],
    [                                                                                        tagM("MDP ★"),    rowB("11.7"),       rowB("1.7"),       rowB("0.13"),       tagS("100 %")],
    [{ text: "30", options: { rowspan: 3, valign: "middle", bold: true, align: "center" } }, tagB("Bayesian"), rowB("31.7"),       rowB("1.7"),       rowB("0.12"),       tagS("100 %")],
    [                                                                                        tagC("CSP"),      rowC("30.0", true), rowC("0.0", true), rowC("0.09", true), tagS("100 %")],
    [                                                                                        tagM("MDP †"),    rowB("30.7"),       rowB("0.7"),       rowB("4.10"),       tagF("0 %")],
    [{ text: "50", options: { rowspan: 3, valign: "middle", bold: true, align: "center" } }, tagB("Bayesian"), rowB("53.0"),       rowB("3.0"),       rowB("0.20"),       tagS("100 %")],
    [                                                                                        tagC("CSP"),      rowC("50.0", true), rowC("0.0", true), rowC("0.15", true), tagS("100 %")],
    [                                                                                        tagM("MDP †"),    rowB("50.7"),       rowB("0.7"),       rowB("8.50"),       tagF("0 %")],
  ];
  s.addTable(data, {
    x: 0.4, y: 0.85, w: 9.2, h: 3.25,
    fontFace: FB, fontSize: 10.5, color: INK,
    border: { pt: 0.5, color: "DCE3EE" }, valign: "middle",
    colW: [0.7, 1.7, 1.5, 1.5, 1.7, 2.1],
  });

  // Three takeaway callouts (Bayesian / CSP / MDP★)
  // -- Bayesian
  s.addShape("rect", { x: 0.4, y: 4.20, w: 3.0, h: 0.90, fill: { color: "FFFFFF" }, line: { color: "DCE3EE", width: 1 } });
  s.addShape("rect", { x: 0.4, y: 4.20, w: 0.08, h: 0.90, fill: { color: DEEP }, line: { color: DEEP } });
  s.addText([
    { text: "Bayesian — ", options: { bold: true, color: DEEP, fontSize: 11 } },
    { text: "low E[L] via τ; sub-ms inference; 5–10 % cycle overhead.",
      options: { color: INK, fontSize: 11 } },
  ], { x: 0.55, y: 4.22, w: 2.80, h: 0.86, fontFace: FB, margin: 0, valign: "middle" });

  // -- CSP
  s.addShape("rect", { x: 3.5, y: 4.20, w: 3.0, h: 0.90, fill: { color: "FFFFFF" }, line: { color: "DCE3EE", width: 1 } });
  s.addShape("rect", { x: 3.5, y: 4.20, w: 0.08, h: 0.90, fill: { color: ACCENT }, line: { color: ACCENT } });
  s.addText([
    { text: "CSP — ", options: { bold: true, color: "B45A1F", fontSize: 11 } },
    { text: "tightest makespan, zero NOPs at n = 30/50; timeout (15 s) for large blocks.",
      options: { color: INK, fontSize: 11 } },
  ], { x: 3.65, y: 4.22, w: 2.80, h: 0.86, fontFace: FB, margin: 0, valign: "middle" });

  // -- MDP ★
  s.addShape("rect", { x: 6.6, y: 4.20, w: 3.0, h: 0.90, fill: { color: "FFFFFF" }, line: { color: "DCE3EE", width: 1 } });
  s.addShape("rect", { x: 6.6, y: 4.20, w: 0.08, h: 0.90, fill: { color: TEAL }, line: { color: TEAL } });
  s.addText([
    { text: "MDP ★ — ", options: { bold: true, color: TEAL, fontSize: 11 } },
    { text: "rescaling penalty −10 → −100 restores 100 % valid at n = 10 (within 6 % of CSP).",
      options: { color: INK, fontSize: 11 } },
  ], { x: 6.75, y: 4.22, w: 2.80, h: 0.86, fontFace: FB, margin: 0, valign: "middle" });

  s.addText("* CP-SAT timeout reached — solution feasible but optimality not proven.   † default reward (−10 / violation).   ★ tuned reward (−100 / violation).",
    { x: 0.4, y: 5.15, w: 9.2, h: 0.22, fontFace: FB, fontSize: 8.5, italic: true, color: MUTED, margin: 0 });

  footer(s, 9, TOTAL);
}

// =====================================================================
// SLIDE 10 — Trade-offs / when to use each
// =====================================================================
{
  const s = pres.addSlide();
  lightBg(s);
  header(s, "Trade-offs", "When to prefer each approach");

  const rows = [
    { label: "Strict cycle distance k required",      bay: "~",  csp: "✓✓", note: "CSP encodes hard constraints natively" },
    { label: "Code-density (minimum NOPs)",            bay: "✓",  csp: "✓✓", note: "CSP minimises makespan globally" },
    { label: "Sub-millisecond compile-time budget",    bay: "✓✓", csp: "✗",  note: "CP-SAT can hit timeout at n ≥ 30" },
    { label: "Soft / probabilistic threat model",      bay: "✓✓", csp: "~",  note: "Bayesian models continuous risk via τ" },
    { label: "Adding business rules (e.g. resource)",  bay: "~",  csp: "✓✓", note: "CSP: one-line model change" },
  ];

  // Header
  s.addShape("rect", { x: 0.4, y: 1.0, w: 9.2, h: 0.4, fill: { color: NAVY }, line: { color: NAVY } });
  s.addText("Scenario",   { x: 0.5, y: 1.0, w: 4.0, h: 0.4, fontFace: FH, fontSize: 12, bold: true, color: "FFFFFF", valign: "middle", margin: 0 });
  s.addText("Bayesian",   { x: 4.5, y: 1.0, w: 1.0, h: 0.4, fontFace: FH, fontSize: 12, bold: true, color: "FFFFFF", align: "center", valign: "middle", margin: 0 });
  s.addText("CSP",        { x: 5.5, y: 1.0, w: 1.0, h: 0.4, fontFace: FH, fontSize: 12, bold: true, color: "FFFFFF", align: "center", valign: "middle", margin: 0 });
  s.addText("Comment",    { x: 6.5, y: 1.0, w: 3.0, h: 0.4, fontFace: FH, fontSize: 12, bold: true, color: "FFFFFF", valign: "middle", margin: 0 });

  rows.forEach((r, i) => {
    const y = 1.4 + i * 0.7;
    if (i % 2 === 0) {
      s.addShape("rect", { x: 0.4, y, w: 9.2, h: 0.7, fill: { color: "FFFFFF" }, line: { color: "FFFFFF" } });
    } else {
      s.addShape("rect", { x: 0.4, y, w: 9.2, h: 0.7, fill: { color: "F0F4F9" }, line: { color: "F0F4F9" } });
    }
    s.addText(r.label, { x: 0.5, y, w: 4.0, h: 0.7, fontFace: FB, fontSize: 11, color: INK, valign: "middle", margin: 0 });
    s.addText(r.bay,   { x: 4.5, y, w: 1.0, h: 0.7, fontFace: FH, fontSize: 14, bold: true, color: DEEP,   align: "center", valign: "middle", margin: 0 });
    s.addText(r.csp,   { x: 5.5, y, w: 1.0, h: 0.7, fontFace: FH, fontSize: 14, bold: true, color: ACCENT, align: "center", valign: "middle", margin: 0 });
    s.addText(r.note,  { x: 6.5, y, w: 3.0, h: 0.7, fontFace: FB, fontSize: 11, italic: true, color: MUTED, valign: "middle", margin: 0 });
  });

  footer(s, 10, TOTAL);
}

// =====================================================================
// SLIDE 11 — Conclusion (dark)
// =====================================================================
{
  const s = pres.addSlide();
  darkBg(s);
  s.addShape("rect", { x: 0, y: 1.6, w: 10, h: 0.04, fill: { color: ACCENT }, line: { color: ACCENT } });

  s.addText("Conclusion", {
    x: 0.6, y: 0.6, w: 8.8, h: 0.8, fontFace: FH, fontSize: 36, bold: true, color: "FFFFFF", margin: 0,
  });

  s.addText([
    { text: "■ ", options: { color: ACCENT, fontSize: 14 } },
    { text: "Three approaches, three regimes: ", options: { bold: true, color: "FFFFFF", fontSize: 14 } },
    { text: "Bayesian inference for soft, probabilistic threat models with sub-millisecond inference; CSP / CP-SAT for strict guarantees and tight makespans; MDP/DQN as a learnable scheduler once the reward is correctly shaped.",
      options: { color: "CADCFC", fontSize: 14, breakLine: true } },
    { text: " ", options: { breakLine: true, fontSize: 6 } },
    { text: "■ ", options: { color: ACCENT, fontSize: 14 } },
    { text: "Reward-shaping is the lesson. ", options: { bold: true, color: "FFFFFF", fontSize: 14 } },
    { text: "Default penalty (−10 / violation) made it rational for the agent to ignore security at large n. Rescaling to −100 restores 100 % valid schedules at n = 10, within 6 % of the CSP optimum — a clean negative-then-positive ablation result.",
      options: { color: "CADCFC", fontSize: 14, breakLine: true } },
    { text: " ", options: { breakLine: true, fontSize: 6 } },
    { text: "■ ", options: { color: ACCENT, fontSize: 14 } },
    { text: "Future work: ", options: { bold: true, color: "FFFFFF", fontSize: 14 } },
    { text: "extend the tuned MDP rerun to n = 30 / 50; extract CPTs from real Cortex-M4 power traces; explore a hybrid CSP + RL architecture where CSP acts as a feasibility oracle for the agent.",
      options: { color: "CADCFC", fontSize: 14 } },
  ], { x: 0.6, y: 1.85, w: 8.8, h: 3.3, fontFace: FB, margin: 0, valign: "top" });

  footer(s, 11, TOTAL);
}

// =====================================================================
// SLIDE 12 — Q&A (dark)
// =====================================================================
{
  const s = pres.addSlide();
  darkBg(s);
  s.addShape("rect", { x: 0, y: 2.5, w: 10, h: 0.05, fill: { color: ACCENT }, line: { color: ACCENT } });

  s.addText("Questions ?", {
    x: 0.6, y: 1.5, w: 8.8, h: 1.0, fontFace: FH, fontSize: 60, bold: true, color: "FFFFFF", align: "center", margin: 0,
  });
  s.addText("Side-Channel-Secure ARM32 Instruction Scheduling — INFO-H410 — Mohamed Tajani", {
    x: 0.6, y: 2.7, w: 8.8, h: 0.5, fontFace: FB, fontSize: 14, italic: true, color: "CADCFC", align: "center", margin: 0,
  });
  s.addText("Code & data:  github.com/<user>/ARM32-Instruction-Scheduling", {
    x: 0.6, y: 3.4, w: 8.8, h: 0.4, fontFace: "Courier New", fontSize: 14, color: ACCENT, align: "center", margin: 0,
  });
  s.addText("INFO-H410 · Université Libre de Bruxelles · 2025–2026", {
    x: 0.6, y: 4.2, w: 8.8, h: 0.4, fontFace: FB, fontSize: 12, color: "CADCFC", align: "center", margin: 0,
  });
}

// =====================================================================
const out = path.resolve(__dirname, "INFO-H410_presentation.pptx");
pres.writeFile({ fileName: out }).then((f) => {
  console.log("Wrote:", f);
});
