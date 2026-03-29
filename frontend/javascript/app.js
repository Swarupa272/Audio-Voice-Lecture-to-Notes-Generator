const API_BASE = "http://127.0.0.1:8000/api";

const uploadForm = document.getElementById("upload-form");
const recordBtn = document.getElementById("record-btn");
const recordStatus = document.getElementById("record-status");
const lectureListEl = document.getElementById("lecture-list");

const detailEmptyEl = document.getElementById("lecture-detail-empty");
const detailEl = document.getElementById("lecture-detail");
const detailTitleEl = document.getElementById("detail-title");
const detailMetaEl = document.getElementById("detail-meta");
const detailStatusEl = document.getElementById("detail-status");
const detailTranscriptEl = document.getElementById("detail-transcript");
const detailNotesEl = document.getElementById("detail-notes");

const generateNotesBtn = document.getElementById("generate-notes-btn");
const exportPdfBtn = document.getElementById("export-pdf-btn");
const exportTxtBtn = document.getElementById("export-txt-btn");
const logoutLink = document.querySelector(".logout-icon");

// RAG & flashcards UI
const summarizeSectionsBtn = document.getElementById("summarize-sections-btn");
const refreshSummariesBtn = document.getElementById("refresh-summaries-btn");
const summariesContainer = document.getElementById("section-summaries");

const askForm = document.getElementById("ask-form");
const askInput = document.getElementById("ask-input");
const askAnswer = document.getElementById("ask-answer");
const askHistoryEl = document.getElementById("ask-history");
const clearHistoryBtn = document.getElementById("clear-history-btn");

const flashcardCountInput = document.getElementById("flashcard-count");
const generateFlashcardsBtn = document.getElementById("generate-flashcards-btn");
const shuffleFlashcardsBtn = document.getElementById("shuffle-flashcards-btn");
const flashcardsContainer = document.getElementById("flashcards");

let currentLectureId = null;
let mediaRecorder = null;
let recordedChunks = [];
let isRecording = false;
let askHistory = [];
let flashcards = [];

function resetLectureState() {
  currentLectureId = null;
  recordedChunks = [];
  isRecording = false;
  lectureListEl.innerHTML = "";
  detailEl.classList.add("hidden");
  detailEmptyEl.classList.remove("hidden");
  detailTranscriptEl.textContent = "";
  detailNotesEl.textContent = "";
  summariesContainer.innerHTML = "";
  askAnswer.textContent = "";
  askInput.value = "";
  askHistory = [];
  renderAskHistory();
  flashcards = [];
  renderFlashcards();
}

if (logoutLink) {
  logoutLink.addEventListener("click", () => {
    // Clear any in-memory UI state before navigating away
    resetLectureState();
    try {
      sessionStorage.clear();
      localStorage.clear();
    } catch (err) {
      console.warn("Storage clear failed", err);
    }
  });
}

function mapStatusToLabel(status) {
  const s = status.toUpperCase();
  if (s === "COMPLETED") return { text: "Completed", cls: "completed" };
  if (s === "TRANSCRIBING" || s === "TRANSCRIBED" || s === "GENERATING_NOTES") {
    return { text: s.replace("_", " ").toLowerCase(), cls: "generating_notes" };
  }
  if (s === "ERROR") return { text: "Error", cls: "error" };
  return { text: "Uploaded", cls: "transcribing" };
}

async function fetchLectures() {
  try {
    const res = await fetch(`${API_BASE}/lectures`);
    if (res.status === 401 || res.status === 403) {
      window.location.href = "/login";
      return;
    }
    if (!res.ok) throw new Error("Failed to fetch lectures");
    const lectures = await res.json();
    renderLectureList(lectures);
  } catch (err) {
    console.error(err);
    resetLectureState();
  }
}

function renderLectureList(lectures) {
  lectureListEl.innerHTML = "";
  if (!Array.isArray(lectures) || lectures.length === 0) {
    const li = document.createElement("li");
    li.textContent = "No lectures yet. Upload or record an audio file.";
    li.className = "lecture-meta";
    lectureListEl.appendChild(li);
    return;
  }

  lectures.forEach((lecture) => {
    const li = document.createElement("li");
    li.className = "lecture-item";
    li.dataset.id = lecture.id;

    const left = document.createElement("div");
    const titleEl = document.createElement("div");
    titleEl.className = "lecture-title";
    titleEl.textContent = lecture.title;
    const metaEl = document.createElement("div");
    metaEl.className = "lecture-meta";
    const parts = [];
    if (lecture.course) parts.push(lecture.course);
    if (lecture.lecturer) parts.push(lecture.lecturer);
    if (lecture.lecture_date) parts.push(lecture.lecture_date);
    metaEl.textContent = parts.join(" • ");
    left.appendChild(titleEl);
    left.appendChild(metaEl);

    const right = document.createElement("div");
    const statusSpan = document.createElement("span");
    const statusInfo = mapStatusToLabel(lecture.status);
    statusSpan.className = `status-pill ${statusInfo.cls}`;
    statusSpan.textContent = statusInfo.text;
    right.appendChild(statusSpan);

    // Add delete button
    const deleteBtn = document.createElement("button");
    deleteBtn.className = "delete-btn";
    deleteBtn.innerHTML = "❌";
    deleteBtn.title = "Delete lecture";
    deleteBtn.addEventListener("click", (e) => {
      e.stopPropagation(); // Prevent triggering the lecture selection
      deleteLecture(lecture.id, lecture.title);
    });
    right.appendChild(deleteBtn);

    li.appendChild(left);
    li.appendChild(right);

    li.addEventListener("click", () => {
      document
        .querySelectorAll(".lecture-item")
        .forEach((el) => el.classList.remove("active"));
      li.classList.add("active");
      showLectureDetail(lecture.id);
    });

    lectureListEl.appendChild(li);
  });
}

function renderSummaries(summaries) {
  summariesContainer.innerHTML = "";
  if (!summaries || summaries.length === 0) {
    summariesContainer.textContent = "No summaries yet.";
    return;
  }
  summaries.forEach((s) => {
    const div = document.createElement("div");
    div.className = "summary-item";
    const title = document.createElement("div");
    title.className = "summary-title";
    title.textContent = s.section_title || "Section";
    const text = document.createElement("div");
    text.className = "summary-text";
    text.textContent = s.summary;
    div.appendChild(title);
    div.appendChild(text);
    summariesContainer.appendChild(div);
  });
}

function renderAskHistory() {
  askHistoryEl.innerHTML = "";
  if (!askHistory.length) return;
  askHistory.slice(-20).forEach((item) => {
    const li = document.createElement("li");
    const q = document.createElement("div");
    q.className = "question";
    q.textContent = item.q;
    const a = document.createElement("div");
    a.className = "answer";
    a.textContent = item.a;
    const s = document.createElement("div");
    s.className = "sources";
    s.textContent = item.sources?.length ? `Sources: ${item.sources.join(", ")}` : "";
    li.appendChild(q);
    li.appendChild(a);
    if (s.textContent) li.appendChild(s);
    askHistoryEl.appendChild(li);
  });
}

function renderFlashcards() {
  flashcardsContainer.innerHTML = "";
  if (!flashcards.length) {
    flashcardsContainer.textContent = "No flashcards yet.";
    return;
  }
  flashcards.forEach((card) => {
    const div = document.createElement("div");
    div.className = "flashcard";
    const q = document.createElement("div");
    q.className = "q";
    q.textContent = `Q: ${card.question}`;
    const a = document.createElement("div");
    a.className = "a";
    a.textContent = `A: ${card.answer}`;
    a.style.display = "none";
    const d = document.createElement("div");
    d.className = "difficulty";
    d.textContent = card.difficulty ? `Difficulty: ${card.difficulty}` : "";
    div.appendChild(q);
    div.appendChild(a);
    if (d.textContent) div.appendChild(d);
    div.addEventListener("click", () => {
      a.style.display = a.style.display === "none" ? "block" : "none";
    });
    flashcardsContainer.appendChild(div);
  });
}

async function showLectureDetail(lectureId) {
  currentLectureId = lectureId;
  try {
    const res = await fetch(`${API_BASE}/lectures/${lectureId}`);
    if (!res.ok) throw new Error("Failed to fetch lecture details");
    const lecture = await res.json();

    detailEmptyEl.classList.add("hidden");
    detailEl.classList.remove("hidden");

    detailTitleEl.textContent = lecture.title;

    const metaParts = [];
    if (lecture.course) metaParts.push(lecture.course);
    if (lecture.lecturer) metaParts.push(lecture.lecturer);
    if (lecture.lecture_date) metaParts.push(lecture.lecture_date);
    detailMetaEl.textContent = metaParts.join(" • ");

    const statusInfo = mapStatusToLabel(lecture.status);
    detailStatusEl.textContent = `Status: ${statusInfo.text}`;

    detailTranscriptEl.textContent =
      lecture.transcript_text || "Transcript not available.";
    detailNotesEl.textContent = lecture.notes_text || "Notes not generated yet.";

    // hydrate summaries/flashcards if already present
    renderSummaries(lecture.section_summaries || []);
    flashcards = lecture.flashcards || [];
    renderFlashcards();
    askAnswer.textContent = "";
    askInput.value = "";
  } catch (err) {
    console.error(err);
    alert("Failed to load lecture details.");
  }
}

uploadForm.addEventListener("submit", async (e) => {
  e.preventDefault();

  const formData = new FormData();
  const title = uploadForm.title.value.trim();
  if (!title) {
    alert("Title is required.");
    return;
  }

  formData.append("title", title);
  formData.append("course", uploadForm.course.value.trim());
  formData.append("lecturer", uploadForm.lecturer.value.trim());
  formData.append("lecture_date", uploadForm.lecture_date.value);

  const fileInput = uploadForm.audio_file;

  if (fileInput.files.length > 0) {
    formData.append("audio_file", fileInput.files[0]);
  } else if (recordedChunks.length > 0) {
    const blob = new Blob(recordedChunks, { type: "audio/webm" });
    formData.append("audio_file", blob, "recording.webm");
  } else {
    alert("Please select an audio file or record from microphone.");
    return;
  }

  const submitBtn = document.getElementById("upload-submit");
  submitBtn.disabled = true;
  submitBtn.textContent = "Uploading & Transcribing...";

  try {
    const res = await fetch(`${API_BASE}/lectures`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const errText = await res.text();
      throw new Error(errText || "Upload failed");
    }
    await res.json();

    recordedChunks = [];
    fileInput.value = "";

    await fetchLectures();
    alert("Lecture uploaded and transcribed successfully.");
  } catch (err) {
    console.error(err);
    alert("Upload or transcription failed. Check backend logs.");
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Upload & Transcribe";
  }
});

recordBtn.addEventListener("click", async () => {
  if (!isRecording) {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder = new MediaRecorder(stream);
      recordedChunks = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          recordedChunks.push(e.data);
        }
      };
      mediaRecorder.onstop = () => {
        recordStatus.textContent = "Recording stopped. Ready to upload.";
      };

      mediaRecorder.start();
      isRecording = true;
      recordBtn.textContent = "Stop Recording";
      recordStatus.textContent = "Recording...";
    } catch (err) {
      console.error(err);
      alert("Unable to access microphone.");
    }
  } else {
    mediaRecorder.stop();
    isRecording = false;
    recordBtn.textContent = "Start Recording";
  }
});

generateNotesBtn.addEventListener("click", async () => {
  if (!currentLectureId) return;
  generateNotesBtn.disabled = true;
  generateNotesBtn.textContent = "Generating...";
  try {
    const res = await fetch(`${API_BASE}/lectures/${currentLectureId}/generate-notes`, {
      method: "POST",
    });
    if (!res.ok) {
      const errText = await res.text();
      throw new Error(errText || "Failed to generate notes");
    }
    const data = await res.json();
    detailNotesEl.textContent = data.notes_text;
    await fetchLectures();
  } catch (err) {
    console.error(err);
    alert("Failed to generate notes. Check Groq API key/model configuration and backend logs.");
  } finally {
    generateNotesBtn.disabled = false;
    generateNotesBtn.textContent = "Generate Notes";
  }
});

async function downloadFile(url, filename) {
  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error("Download failed");
    const blob = await res.blob();
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(link.href);
  } catch (err) {
    console.error(err);
    alert("Download failed.");
  }
}

exportPdfBtn.addEventListener("click", async () => {
  if (!currentLectureId) return;
  await downloadFile(
    `${API_BASE}/lectures/${currentLectureId}/export?format=pdf`,
    "lecture_notes.pdf"
  );
});

exportTxtBtn.addEventListener("click", async () => {
  if (!currentLectureId) return;
  await downloadFile(
    `${API_BASE}/lectures/${currentLectureId}/export?format=txt`,
    "lecture_notes.txt"
  );
});

async function fetchSectionSummaries(force = false) {
  if (!currentLectureId) return;
  summarizeSectionsBtn.disabled = true;
  refreshSummariesBtn.disabled = true;
  summariesContainer.textContent = "Loading summaries...";
  summariesContainer.dataset.error = "";
  const forceParam = force ? "?force=true" : "";
  try {
    const res = await fetch(
      `${API_BASE}/lectures/${currentLectureId}/summaries/sections${forceParam}`,
      { method: "POST", credentials: "include" }
    );
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    renderSummaries(data.summaries || []);
  } catch (err) {
    console.error(err);
    summariesContainer.textContent = "Failed to load summaries.";
    summariesContainer.dataset.error = err?.message || "Unknown error";
    alert("Summaries failed: " + (err?.message || "Unknown error"));
  } finally {
    summarizeSectionsBtn.disabled = false;
    refreshSummariesBtn.disabled = false;
  }
}

async function askNotes(question) {
  if (!currentLectureId || !question.trim()) return;
  askAnswer.textContent = "Thinking...";
  askAnswer.dataset.error = "";
  try {
    const res = await fetch(`${API_BASE}/lectures/${currentLectureId}/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ query: question }),
    });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    askAnswer.textContent = data.answer || "No answer.";
    askHistory.push({ q: question, a: data.answer || "", sources: data.sources || [] });
    renderAskHistory();
  } catch (err) {
    console.error(err);
    askAnswer.textContent = "Failed to get answer.";
    askAnswer.dataset.error = err?.message || "Unknown error";
    alert("Ask failed: " + (err?.message || "Unknown error"));
  }
}

async function generateFlashcards(count) {
  if (!currentLectureId) return;
  generateFlashcardsBtn.disabled = true;
  generateFlashcardsBtn.textContent = "Generating...";
  try {
    const res = await fetch(
      `${API_BASE}/lectures/${currentLectureId}/flashcards?count=${count || 8}`,
      { method: "POST", credentials: "include" }
    );
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    flashcards = data.flashcards || [];
    renderFlashcards();
  } catch (err) {
    console.error(err);
    alert("Failed to generate flashcards: " + (err?.message || "Unknown error"));
  } finally {
    generateFlashcardsBtn.disabled = false;
    generateFlashcardsBtn.textContent = "Generate";
  }
}

function shuffleFlashcards() {
  for (let i = flashcards.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [flashcards[i], flashcards[j]] = [flashcards[j], flashcards[i]];
  }
  renderFlashcards();
}

// Summaries events
if (summarizeSectionsBtn) {
  summarizeSectionsBtn.addEventListener("click", () => fetchSectionSummaries(false));
}
if (refreshSummariesBtn) {
  refreshSummariesBtn.addEventListener("click", () => fetchSectionSummaries(true));
}

// Ask-the-notes events
if (askForm) {
  askForm.addEventListener("submit", (e) => {
    e.preventDefault();
    askNotes(askInput.value);
  });
}
if (clearHistoryBtn) {
  clearHistoryBtn.addEventListener("click", () => {
    askHistory = [];
    renderAskHistory();
  });
}

// Flashcards events
if (generateFlashcardsBtn) {
  generateFlashcardsBtn.addEventListener("click", () => {
    const count = Number(flashcardCountInput.value) || 8;
    generateFlashcards(count);
  });
}
if (shuffleFlashcardsBtn) {
  shuffleFlashcardsBtn.addEventListener("click", () => {
    if (!flashcards.length) return;
    shuffleFlashcards();
  });
}

async function deleteLecture(lectureId, lectureTitle) {
  if (!confirm(`Are you sure you want to delete "${lectureTitle}"? This cannot be undone.`)) {
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/lectures/${lectureId}`, {
      method: "DELETE",
    });
    if (!res.ok) {
      const errText = await res.text();
      throw new Error(errText || "Delete failed");
    }

    // If the deleted lecture is currently selected, hide the detail view
    if (currentLectureId === lectureId) {
      currentLectureId = null;
      detailEl.classList.add("hidden");
      detailEmptyEl.classList.remove("hidden");
    }

    await fetchLectures();
    alert("Lecture deleted successfully.");
  } catch (err) {
    console.error(err);
    alert("Failed to delete lecture.");
  }
}

fetchLectures();

