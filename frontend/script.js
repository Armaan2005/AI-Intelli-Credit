// ── Config ───────────────────────────────────────────────────────────────────
const BASE_URL = "https://ai-intelli-credit.onrender.com";

// ── State ────────────────────────────────────────────────────────────────────
let lastFilePath    = "";
let lastResult      = null;
let lastCompanyName = "";
let stepTimer       = null;

// ── On page load ─────────────────────────────────────────────────────────────
window.onerror = function(message, source, lineno, colno, error) {
  showError("JS Error: " + message);
};

// ── File Selection ────────────────────────────────────────────────────────────
function onFileSelected(input) {
  const file = input.files[0];
  if (file) {
    document.getElementById("fileName").textContent = `✓ ${file.name}`;
  }
}

// ── Drag & Drop ───────────────────────────────────────────────────────────────
const zone = document.getElementById("uploadZone");
if (zone) {
  zone.addEventListener("dragover", e => {
    e.preventDefault();
    zone.classList.add("dragover");
  });
  zone.addEventListener("dragleave", () => zone.classList.remove("dragover"));
  zone.addEventListener("drop", e => {
    e.preventDefault();
    zone.classList.remove("dragover");
    const file = e.dataTransfer.files[0];
    if (file) {
      document.getElementById("fileInput").files = e.dataTransfer.files;
      document.getElementById("fileName").textContent = `✓ ${file.name}`;
    }
  });
}

// ── Loading Steps ─────────────────────────────────────────────────────────────
function startSteps() {
  const steps = ["step1","step2","step3","step4","step5","step6"];
  let i = 0;

  // Reset all
  steps.forEach(s => {
    const el = document.getElementById(s);
    if (el) el.classList.remove("active", "done");
  });

  // Activate first
  const first = document.getElementById(steps[0]);
  if (first) first.classList.add("active");

  stepTimer = setInterval(() => {
    const cur = document.getElementById(steps[i]);
    if (cur) cur.classList.replace("active", "done");
    i++;
    if (i < steps.length) {
      const next = document.getElementById(steps[i]);
      if (next) next.classList.add("active");
    } else {
      clearInterval(stepTimer);
    }
  }, 2000);
}

function stopSteps() {
  clearInterval(stepTimer);
}

// ── Main Analysis ─────────────────────────────────────────────────────────────
async function uploadFile() {
  // Support both button names — your original was uploadFile()
  await runAnalysis();
}

async function runAnalysis() {
  const fileInput    = document.getElementById("fileInput");
  const companyName  = (document.getElementById("companyName")?.value  || "").trim();
  const promoterName = (document.getElementById("promoterName")?.value || "").trim();
  const loanAmount   = parseFloat(document.getElementById("loanAmount")?.value) || 0;
  const docType      = document.getElementById("docType")?.value || "other";
  const factoryCap   = parseFloat(document.getElementById("factoryCap")?.value) || null;
  const siteNotes    = (document.getElementById("siteNotes")?.value || "").trim();

  if (!fileInput?.files[0]) {
    showError("Please select a file first.");
    return;
  }

  hideError();
  showLoading(true);
  hideResults();
  setBtn(true);
  startSteps();
  lastCompanyName = companyName || "Company";

  try {
    // ── STEP 1: Upload ──────────────────────────────────────────────────────
    const formData = new FormData();
    formData.append("file",     fileInput.files[0]);
    formData.append("doc_type", docType);
    formData.append("app_id",   "demo");

    const uploadRes = await fetch(`${BASE_URL}/upload/`, {
      method: "POST",
      body: formData,
    });

    if (!uploadRes.ok) {
      const err = await uploadRes.text();
      throw new Error(`Upload failed (${uploadRes.status}): ${err}`);
    }

    const uploadData = await uploadRes.json();
    console.log("✅ Upload:", uploadData);
    lastFilePath = uploadData.path;

    // ── STEP 2: Analyze ─────────────────────────────────────────────────────
    // FIXED: JSON body instead of exposing path in URL
    const analyzeRes = await fetch(`${BASE_URL}/analyze/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        file_path:            lastFilePath,
        app_id:               "demo",
        company_name:         companyName,
        promoter_name:        promoterName,
        loan_amount:          loanAmount,
        factory_capacity_pct: factoryCap,
        site_visit_notes:     siteNotes,
      }),
    });

    console.log("📊 Analyze status:", analyzeRes.status);

    if (!analyzeRes.ok) {
      const errText = await analyzeRes.text();
      throw new Error(`Analysis failed (${analyzeRes.status}): ${errText}`);
    }

    lastResult = await analyzeRes.json();
    console.log("✅ Result:", lastResult);

    if (lastResult.error) throw new Error(lastResult.error);

    stopSteps();
    showLoading(false);
    renderResults(lastResult);

  } catch (err) {
    console.error("❌ Error:", err);
    stopSteps();
    showLoading(false);
    showError("Error: " + err.message);
  } finally {
    setBtn(false);
  }
}

// ── Render Results ────────────────────────────────────────────────────────────
function renderResults(r) {
  // ── Decision Banner ─────────────────────────────────────────────────────
  const decision = r.decision || "N/A";
  const banner   = document.getElementById("decisionBanner");
  if (banner) {
    const cls = decision.toLowerCase().includes("reject")    ? "reject"
              : decision.toLowerCase().includes("condition") ? "refer"
              : "approve";
    banner.className = `decision-banner ${cls}`;

    const heading = document.getElementById("decisionHeading");
    const sub     = document.getElementById("decisionSub");
    const badge   = document.getElementById("decisionBadge");
    if (heading) heading.textContent = decision;
    if (sub)     sub.textContent     = r.meta?.company ? `Application for ${r.meta.company}` : "Credit Decision";
    if (badge)   badge.textContent   = r.rating || "N/A";
  }

  // ── Stats ────────────────────────────────────────────────────────────────
  setText("statScore",  r.total_score ? Math.round(r.total_score) : "—");
  setText("statRating", r.rating       || "—");
  setText("statAmount", r.loan_amount  ? `₹${r.loan_amount}L`    : "—");
  setText("statRate",   r.interest_rate || "—");

  // ── Score Ring ───────────────────────────────────────────────────────────
  const score  = r.total_score || 0;
  const circ   = 2 * Math.PI * 52;
  const circle = document.getElementById("scoreCircle");
  const ringNum = document.getElementById("ringNum");
  if (circle)  circle.style.strokeDashoffset = circ - (score / 100) * circ;
  if (ringNum) ringNum.textContent = Math.round(score);

  // ── Five Cs Bars ─────────────────────────────────────────────────────────
  const fiveC = r.five_c_scores || {};
  const dims  = [
    { key: "character",  label: "Character",  color: "#00B4D8" },
    { key: "capacity",   label: "Capacity",   color: "#22C55E" },
    { key: "capital",    label: "Capital",    color: "#F4A261" },
    { key: "collateral", label: "Collateral", color: "#A78BFA" },
    { key: "conditions", label: "Conditions", color: "#FB923C" },
  ];
  const barsEl = document.getElementById("fiveCBars");
  if (barsEl) {
    barsEl.innerHTML = dims.map(d => {
      const val = Math.round(fiveC[d.key] || 0);
      return `
        <div class="five-c-row">
          <span class="c-label">${d.label}</span>
          <div class="c-bar-wrap">
            <div class="c-bar" style="width:${val}%;background:${d.color}"></div>
          </div>
          <span class="c-score" style="color:${d.color}">${val}</span>
        </div>`;
    }).join("");
  }

  // ── Rationale ────────────────────────────────────────────────────────────
  const rationale = r.rationale || r.explainability?.narrative || "No rationale available.";
  setText("rationaleText", rationale);

  // ── Conditions ───────────────────────────────────────────────────────────
  const conditions   = r.conditions || [];
  const condWrap     = document.getElementById("conditionsWrap");
  const condList     = document.getElementById("conditionsList");
  if (condWrap && condList && conditions.length) {
    condWrap.classList.remove("hidden");
    condList.innerHTML = conditions.map(c => `<li>${c}</li>`).join("");
  }

  // ── Research ─────────────────────────────────────────────────────────────
  const res = r.research || {};
  const riskColor = v => v === "High" ? "risk-high" : v === "Medium" ? "risk-medium" : "risk-low";
  const resGrid = document.getElementById("researchGrid");
  if (resGrid) {
    resGrid.innerHTML = [
      { label: "Fraud Risk",       value: res.fraud_risk        || "N/A" },
      { label: "Legal Risk",       value: res.legal_risk        || "N/A" },
      { label: "Sector Risk",      value: res.sector_risk       || "N/A" },
      { label: "MCA Risk",         value: res.mca_risk          || "N/A" },
      { label: "Wilful Defaulter", value: res.wilful_defaulter  ? "⚠️ YES" : "✓ No" },
      { label: "Reputation",       value: res.reputation        || "N/A" },
    ].map(item => `
      <div class="research-item">
        <div class="r-label">${item.label}</div>
        <div class="r-value ${riskColor(item.value)}">${item.value}</div>
      </div>`
    ).join("");
  }

  const resSummary = document.getElementById("researchSummary");
  if (resSummary && res.overall_risk_summary) {
    resSummary.style.display = "block";
    resSummary.textContent   = res.overall_risk_summary;
  }

  // ── Risk Flags ───────────────────────────────────────────────────────────
  const flags   = r.risk_flags || [];
  const flagsEl = document.getElementById("flagsList");
  const flagCard = document.getElementById("flagsCard");
  if (flagsEl && flags.length) {
    flagsEl.innerHTML = flags.map(f => {
      const cls = f.includes("🚨") ? "critical" : f.includes("⚠️") ? "warning" : "info";
      return `<div class="flag-item ${cls}">${f}</div>`;
    }).join("");
  } else if (flagCard) {
    flagCard.style.display = "none";
  }

  // ── Also update your original #result div (backward compat) ─────────────
  const oldResult = document.getElementById("result");
  if (oldResult) {
    const expl    = r.explainability || {};
    const reasons = Array.isArray(expl.reasons) ? expl.reasons.join(", ") : "—";
    oldResult.innerHTML = `
      <h2>📊 Risk: ${r.risk_level || "N/A"}</h2>
      <p>💰 <b>Loan Amount:</b> ₹${r.loan_amount || "N/A"}</p>
      <p>📉 <b>Interest Rate:</b> ${r.interest_rate || "N/A"}</p>
      <p>🤖 <b>Decision:</b> ${r.decision || "N/A"}</p>
      <p>⚡️ <b>Score:</b> ${r.total_score || "N/A"}</p>
      <p>🚨 <b>Fraud Risk:</b> ${res.fraud_risk || "N/A"}</p>
      <p>⚖️ <b>Legal Risk:</b> ${res.legal_risk || "N/A"}</p>
      <p>💡 <b>Reasons:</b> ${reasons}</p>
    `;
  }

  showResults();
  document.getElementById("results")?.scrollIntoView({ behavior: "smooth" });
}

// ── Download CAM PDF ──────────────────────────────────────────────────────────
async function downloadReport() {
  if (!lastResult) { showError("Run analysis first."); return; }

  const btn = document.getElementById("downloadBtn");
  if (btn) { btn.disabled = true; btn.textContent = "Generating..."; }

  try {
    const res = await fetch(`${BASE_URL}/report/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        analysis_result: lastResult,
        company_name:    lastCompanyName,
      }),
    });

    if (!res.ok) throw new Error("Report generation failed");

    const blob     = await res.blob();
    const url      = URL.createObjectURL(blob);
    const a        = document.createElement("a");
    a.href         = url;
    a.download     = `CAM_${lastCompanyName.replace(/\s+/g, "_")}_Report.pdf`;
    a.click();
    URL.revokeObjectURL(url);

  } catch (err) {
    showError("Report error: " + err.message);
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = "⬇ Download CAM PDF"; }
  }
}

// ── Reset ─────────────────────────────────────────────────────────────────────
function resetForm() {
  hideResults();
  const ids = ["fileInput","companyName","promoterName","loanAmount","factoryCap","siteNotes"];
  ids.forEach(id => { const el = document.getElementById(id); if (el) el.value = ""; });

  setText("fileName", "");
  document.getElementById("conditionsWrap")?.classList.add("hidden");
  const rs = document.getElementById("researchSummary");
  if (rs) rs.style.display = "none";
  const fc = document.getElementById("flagsCard");
  if (fc) fc.style.display = "";
  hideError();
  lastFilePath = ""; lastResult = null;
  window.scrollTo({ top: 0, behavior: "smooth" });
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}
function showLoading(show) {
  const el = document.getElementById("loading");
  if (el) el.classList.toggle("show", show);
}
function showResults() {
  document.getElementById("results")?.classList.remove("hidden");
}
function hideResults() {
  document.getElementById("results")?.classList.add("hidden");
}
function showError(msg) {
  const el = document.getElementById("errorBox");
  if (!el) { alert(msg); return; }
  el.textContent = msg;
  el.classList.remove("hidden");
}
function hideError() {
  document.getElementById("errorBox")?.classList.add("hidden");
}
function setBtn(disabled) {
  const btn = document.getElementById("analyzeBtn");
  if (btn) btn.disabled = disabled;
}