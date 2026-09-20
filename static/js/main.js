const PRESETS = window.PRESETS || {};

function switchTab(tab) {
  document.querySelectorAll(".tab").forEach(t => t.classList.toggle("active", t.dataset.tab === tab));
  document.querySelectorAll(".view").forEach(v => v.classList.toggle("active", v.id === `view-${tab}`));
  if (tab === "progress") loadProgress();
  if (tab === "home") loadStats();
}

document.getElementById("tabs").addEventListener("click", (e) => {
  if (e.target.classList.contains("tab")) switchTab(e.target.dataset.tab);
});

document.getElementById("presetSelect").addEventListener("change", (e) => {
  const preset = PRESETS[e.target.value];
  if (!preset) return;
  document.getElementById("subjectInput").value = preset.subject;
  document.getElementById("topicsInput").value = preset.topics.join("\n");
});

async function loadStats() {
  try {
    const studentId = localStorage.getItem("studentId") || "Student";
    const r = await fetch(`/api/stats?student=${encodeURIComponent(studentId)}`);
    const d = await r.json();
    document.getElementById("statUnits").textContent = d.units;
    document.getElementById("statTopics").textContent = d.topics;
    document.getElementById("statWatched").textContent = d.watched;
  } catch (e) { /* silent */ }
}

async function loadProgress() {
  const student = document.getElementById("studentName").value || "Student";
  const box = document.getElementById("progressList");
  try {
    const r = await fetch(`/api/progress?student=${encodeURIComponent(student)}`);
    const units = await r.json();
    if (!units.length) {
      box.innerHTML = `<p class="empty-note">No units mapped yet. Head to <button class="link-btn" onclick="switchTab('find')">Find my topics</button> to get started.</p>`;
      return;
    }
    // Group units by subject
    const bySubject = {};
    for (const u of units) {
      if (!bySubject[u.subject]) bySubject[u.subject] = [];
      bySubject[u.subject].push(u);
    }
    
    let html = "";
    for (const [subject, subjUnits] of Object.entries(bySubject)) {
      html += `<div class="subject-folder" style="margin-bottom:2rem;">
        <h3 class="subject-title" style="margin-bottom:1rem; border-bottom:1px solid rgba(255,255,255,0.1); padding-bottom:0.5rem; color:var(--brand-yellow);">${escapeHtml(subject)}</h3>
        <div class="subject-units" style="display:flex; flex-direction:column; gap:1rem;">
          ${subjUnits.map(u => `
            <div class="progress-card">
              <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                <h4 style="cursor:pointer; display:flex; align-items:center; gap:0.5rem;" onclick="toggleTopics(${u.id})">${escapeHtml(u.unit_label)} <span style="font-size:0.7em; opacity:0.7;">▼</span></h4>
                <button onclick="deleteUnit(${u.id})" style="background:none; border:none; color:#d32f2f; cursor:pointer; font-size:14px; text-decoration:underline;">Remove</button>
              </div>
              <div class="progress-track"><div class="progress-fill" style="width:${u.pct}%"></div></div>
              <div class="progress-caption">${u.pct}% watched (${u.watched}/${u.total} topics)</div>
              <div id="topics-${u.id}" style="display:none; margin-top:15px; padding-top:15px; border-top:1px solid rgba(255,255,255,0.1); display:flex; flex-direction:column; gap:0.5rem;">
                ${u.topics.map(t => `
                  <div style="font-size:0.9em; background:rgba(255,255,255,0.03); padding:0.5rem; border-radius:4px;">
                    <div style="margin-bottom:0.2rem; opacity:0.9;">${escapeHtml(t.topic)}</div>
                    ${t.url !== "#" ? `<a href="${t.url}" target="_blank" style="color:#60a5fa; text-decoration:none;">▶ Watch: ${escapeHtml(t.title)}</a>` : `<span style="color:#d32f2f">Search Failed</span>`}
                  </div>
                `).join("")}
              </div>
            </div>
          `).join("")}
        </div>
      </div>`;
    }
    box.innerHTML = html;
    
    // Hide all topics by default (the inline style above momentarily sets display:flex, so fix it here)
    units.forEach(u => document.getElementById("topics-"+u.id).style.display = "none");
  } catch (e) {
    box.innerHTML = `<p class="empty-note">Couldn't load progress right now.</p>`;
  }
}

window.toggleTopics = function(id) {
  const el = document.getElementById("topics-" + id);
  if (el.style.display === "none") {
    el.style.display = "flex";
  } else {
    el.style.display = "none";
  }
};

window.deleteUnit = async function(unitId) {
  if (!confirm("Remove this unit from your history?")) return;
  try {
    await fetch("/api/delete_unit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ unit_id: unitId })
    });
    loadProgress();
  } catch (e) {
    alert("Couldn't remove unit.");
  }
};

function escapeHtml(s) {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

document.getElementById("findForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const student = document.getElementById("studentName").value || "Student";
  const subject = document.getElementById("subjectInput").value.trim();
  localStorage.setItem("savedSubject", subject);
  const unit_label = document.getElementById("unitInput").value.trim();
  const topics = document.getElementById("topicsInput").value
    .split("\n").map(t => t.trim()).filter(Boolean);

  const status = document.getElementById("findStatus");
  const submitBtn = document.getElementById("findSubmit");
  const resultsList = document.getElementById("resultsList");
  const multiBox = document.getElementById("multiTopicBox");

  if (!subject || !topics.length) {
    status.textContent = "Enter a subject and at least one topic.";
    status.className = "find-status error";
    return;
  }

  submitBtn.disabled = true;
  status.className = "find-status";
  status.textContent = `Searching for ${topics.length} topic${topics.length > 1 ? "s" : ""}...`;
  resultsList.innerHTML = "";
  multiBox.hidden = true;

  try {
    const r = await fetch("/api/find_topics", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ student, subject, unit_label, topics }),
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.error || "Something went wrong");

    status.textContent = `Matched ${data.results.length} topic${data.results.length > 1 ? "s" : ""} for ${subject}${unit_label ? " — " + unit_label : ""}.`;

    if (data.multi_topic_videos.length) {
      multiBox.hidden = false;
      multiBox.innerHTML = `<h3>Efficient pick${data.multi_topic_videos.length > 1 ? "s" : ""} found</h3>
        <ul>${data.multi_topic_videos.map(m =>
          `<li><strong>${escapeHtml(m.title)}</strong> already covers: ${m.topics.map(escapeHtml).join(", ")}</li>`
        ).join("")}</ul>`;
    }

    resultsList.innerHTML = data.results.map(res => `
      <div class="result-row">
        <div>
          <div class="result-topic">${escapeHtml(res.topic)}</div>
          ${res.error 
            ? `<div class="result-meta"><span style="color:#d32f2f">Search Failed: ${escapeHtml(res.error)}</span></div>`
            : `<div class="result-meta">
                <span class="result-badge">${res.timestamp}</span>
                ${escapeHtml(res.title)} · ${escapeHtml(res.channel)} · ${res.view_count.toLocaleString()} views
               </div>
               ${res.url !== "#"
                 ? `<a class="result-link" href="${res.url}" target="_blank" rel="noopener">Watch this segment ▶</a>`
                 : `<span class="result-demo-note">Demo mode — no real link available</span>`}`
          }
        </div>
        <label class="watch-toggle">
          <input type="checkbox" data-id="${res.id}" ${res.watched ? "checked" : ""}>
          Watched
        </label>
      </div>
    `).join("");

    resultsList.querySelectorAll("input[type=checkbox]").forEach(cb => {
      cb.addEventListener("change", async (e) => {
        await fetch("/api/mark_watched", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ id: e.target.dataset.id, watched: e.target.checked }),
        });
      });
    });

  } catch (err) {
    status.textContent = "Couldn't fetch results: " + err.message;
    status.className = "find-status error";
  } finally {
    submitBtn.disabled = false;
  }
});

// loadStats is now called inside DOMContentLoaded

document.addEventListener("DOMContentLoaded", () => {
  let studentId = localStorage.getItem("studentId");
  if (!studentId) {
    // Generate a random 6-character ID for this user's browser session
    studentId = "User_" + Math.random().toString(36).substring(2, 8).toUpperCase();
    localStorage.setItem("studentId", studentId);
  }
  document.getElementById("studentName").value = studentId;

  document.getElementById("studentName").value = studentId;

  const savedSubject = localStorage.getItem("savedSubject");
  if (savedSubject) document.getElementById("subjectInput").value = savedSubject;
  
  loadStats();
});
