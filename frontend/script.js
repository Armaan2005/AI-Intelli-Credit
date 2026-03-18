window.onerror = function(message, source, lineno, colno, error) {
  alert("JS ERROR: " + message);
};
let lastFilePath="";
async function uploadFile() {
  try {
    const fileInput = document.getElementById("fileInput");
    const file = fileInput.files[0];

    if (!file) {
      alert("Select file first");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    document.getElementById("loading").classList.remove("hidden");

    // 🔹 Upload
    const uploadRes = await fetch("http://127.0.0.1:8000/upload/", {
      method: "POST",
      body: formData
    });

    const uploadData = await uploadRes.json();
    console.log("UPLOAD:", uploadData);

    lastFilePath=uploadData.path;

    // 🔥 ANALYZE CALL
    const url = `http://127.0.0.1:8000/analyze/?file_path=${encodeURIComponent(uploadData.path)}`;
    console.log("ANALYZE URL:", url);

    const analyzeRes = await fetch(url, { method: "POST" });

    console.log("STATUS:", analyzeRes.status);

    if (!analyzeRes.ok) {
      const errText = await analyzeRes.text();
      alert("Backend Error: " + errText);
      document.getElementById("loading").classList.add("hidden");
      return;
    }

    const result = await analyzeRes.json();
    console.log("RESULT:", result);

    document.getElementById("loading").classList.add("hidden");

 const reasons = Array.isArray(result.reasons)
  ? result.reasons.join(", ")
  : (result.reasons ? String(result.reasons) : "No reasons available");

const decision = typeof result.decision === "string"
  ? result.decision
  : JSON.stringify(result.decision);

document.getElementById("result").innerHTML = `
  <h2>📊 Risk: ${result.risk}</h2>

  <p>💰 <b>Loan Amount:</b> ₹${result.loan_amount}</p>
  <p>📉 <b>Interest Rate:</b> ${result.interest_rate}</p>

  <p>🤖 <b>Decision:</b> ${result.decision}</p>
  <p>⚡️ <b>Score:</b> ${result.score}</p>

  <p>🚨 <b>Fraud Risk:</b> ${result.research.fraud_risk}</p>
  <p>⚖️ <b>Legal Risk:</b> ${result.research.legal_risk}</p>

  <p>💡 <b>Reasons:</b> ${reasons}</p>
  <button onclick="downloadReport()">Download Report</button>
  
  `
;

  } catch (err) {
    console.error("ERROR:", err);
    alert("Error: " + err.message);
    document.getElementById("loading").classList.add("hidden");
  }
}

function downloadReport(){
  if(!lastFilePath){
    alert("Analyze first");
    return;
  }
  const url=`http://127.0.0.1:8000/analyze/report?file_path=${encodeURIComponent(lastFilePath)}`;
  window.open(url,"_blank");
}