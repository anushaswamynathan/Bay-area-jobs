const state = {
  criteria: {},
  digestsByDate: {},
  selectedDateKey: getDateKey(new Date()),
  visibleMonth: startOfMonth(new Date()),
  activeFilter: "all",
  criteriaPanelOpen: false,
  calendarPanelOpen: false,
};

const elements = {
  activeDateCaption: document.querySelector("#active-date-caption"),
  todayLabel: document.querySelector("#today-label"),
  digestSummary: document.querySelector("#digest-summary"),
  criteriaList: document.querySelector("#criteria-list"),
  criteriaPanel: document.querySelector("#criteria-panel"),
  calendarPanel: document.querySelector("#calendar-panel"),
  jobCount: document.querySelector("#job-count"),
  publicCount: document.querySelector("#public-count"),
  shortlistedCount: document.querySelector("#shortlisted-count"),
  openImportDialog: document.querySelector("#open-import-dialog"),
  toggleCriteria: document.querySelector("#toggle-criteria"),
  toggleCalendar: document.querySelector("#toggle-calendar"),
  importDialog: document.querySelector("#import-dialog"),
  importForm: document.querySelector("#import-form"),
  closeImportDialog: document.querySelector("#close-import-dialog"),
  importDateInput: document.querySelector("#import-date-input"),
  importJsonInput: document.querySelector("#import-json-input"),
  importStatus: document.querySelector("#import-status"),
  exactJobList: document.querySelector("#exact-job-list"),
  overlapJobList: document.querySelector("#overlap-job-list"),
  emptyState: document.querySelector("#empty-state"),
  jobTemplate: document.querySelector("#job-card-template"),
  calendarMonthLabel: document.querySelector("#calendar-month-label"),
  calendarGrid: document.querySelector("#calendar-grid"),
  previousMonth: document.querySelector("#previous-month"),
  nextMonth: document.querySelector("#next-month"),
  jumpToday: document.querySelector("#jump-today"),
  filterChips: Array.from(document.querySelectorAll(".filter-chip")),
};

boot();

async function boot() {
  await refreshState();
  syncSelectedDate();
  render();
  wireEvents();
}

function wireEvents() {
  elements.previousMonth.addEventListener("click", () => changeVisibleMonth(-1));
  elements.nextMonth.addEventListener("click", () => changeVisibleMonth(1));
  elements.jumpToday.addEventListener("click", jumpToToday);
  elements.openImportDialog.addEventListener("click", openImportDialog);
  elements.toggleCriteria.addEventListener("click", () => toggleUtilityPanel("criteria"));
  elements.toggleCalendar.addEventListener("click", () => toggleUtilityPanel("calendar"));
  elements.closeImportDialog.addEventListener("click", () => elements.importDialog.close());
  elements.importForm.addEventListener("submit", handleImportSubmit);
  elements.filterChips.forEach((chip) => {
    chip.addEventListener("click", () => {
      state.activeFilter = chip.dataset.filter;
      render();
    });
  });
}

function toggleUtilityPanel(panelName) {
  if (panelName === "criteria") {
    state.criteriaPanelOpen = !state.criteriaPanelOpen;
  }
  if (panelName === "calendar") {
    state.calendarPanelOpen = !state.calendarPanelOpen;
  }
  renderUtilityPanels();
}

async function refreshState() {
  const response = await fetch("/api/state");
  const payload = await response.json();
  state.criteria = payload.criteria || {};
  state.digestsByDate = payload.digestsByDate || {};
}

function openImportDialog() {
  const selectedDigest = getSelectedDigest();
  elements.importDateInput.value = state.selectedDateKey;
  elements.importJsonInput.value = JSON.stringify(
    {
      date: state.selectedDateKey,
      summary: selectedDigest?.summary || "Fresh daily digest",
      criteria: state.criteria,
      jobs: selectedDigest?.jobs || [],
    },
    null,
    2
  );
  elements.importStatus.hidden = true;
  elements.importDialog.showModal();
}

async function handleImportSubmit(event) {
  event.preventDefault();
  let payload;

  try {
    payload = JSON.parse(elements.importJsonInput.value);
  } catch (error) {
    elements.importStatus.hidden = false;
    elements.importStatus.textContent = "That JSON is invalid. Double-check the payload and try again.";
    return;
  }

  if (elements.importDateInput.value) {
    payload.date = elements.importDateInput.value;
  }

  const response = await fetch("/api/import-digest", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    elements.importStatus.hidden = false;
    elements.importStatus.textContent = "Import failed. Make sure each job has a title, company, and link.";
    return;
  }

  await refreshState();
  state.selectedDateKey = payload.date || getDateKey(new Date());
  state.visibleMonth = startOfMonth(new Date(`${state.selectedDateKey}T12:00:00`));
  render();
  elements.importDialog.close();
}

function render() {
  const digest = getSelectedDigest();
  const allJobs = sortJobs(digest?.jobs || []);
  const filteredJobs = applyFilter(allJobs);
  const exactJobs = filteredJobs.filter((job) => job.salaryBandFit === "exact");
  const overlapJobs = filteredJobs.filter((job) => job.salaryBandFit !== "exact");
  const publicCount = allJobs.filter((job) => job.companyStatus === "public").length;
  const shortlistedCount = allJobs.filter((job) => job.shortlisted).length;
  const appliedCount = allJobs.filter((job) => job.applied).length;

  elements.activeDateCaption.textContent = getRelativeDateLabel(state.selectedDateKey);
  elements.todayLabel.textContent = formatDateLabel(state.selectedDateKey);
  elements.digestSummary.textContent =
    digest?.summary || "No digest is available for this date yet.";
  elements.jobCount.textContent = String(allJobs.length);
  elements.publicCount.textContent = String(publicCount);
  elements.shortlistedCount.textContent = String(appliedCount || shortlistedCount);
  elements.exactJobList.innerHTML = "";
  elements.overlapJobList.innerHTML = "";
  elements.emptyState.hidden = filteredJobs.length > 0;

  renderCriteria();
  renderFilterState();
  renderUtilityPanels();
  exactJobs.forEach((job) => {
    elements.exactJobList.appendChild(createJobCard(job));
  });
  overlapJobs.forEach((job) => {
    elements.overlapJobList.appendChild(createJobCard(job));
  });
  renderCalendar();
}

function renderUtilityPanels() {
  elements.criteriaPanel.hidden = !state.criteriaPanelOpen;
  elements.calendarPanel.hidden = !state.calendarPanelOpen;
  elements.toggleCriteria.classList.toggle("is-active", state.criteriaPanelOpen);
  elements.toggleCalendar.classList.toggle("is-active", state.calendarPanelOpen);
}

function renderCriteria() {
  const items = [
    `Location: ${state.criteria.location || "Bay Area"}`,
    `Salary: ${state.criteria.salary || "$190,000-$220,000"}`,
    `Focus: ${(state.criteria.industries || []).join(" + ")}`,
    `Sources: ${(state.criteria.sources || []).join(", ")}`,
    `Ranking: ${state.criteria.ranking || "Public first"}`,
  ];

  elements.criteriaList.innerHTML = "";
  items.forEach((item) => {
    const entry = document.createElement("li");
    entry.textContent = item;
    elements.criteriaList.appendChild(entry);
  });
}

function renderFilterState() {
  elements.filterChips.forEach((chip) => {
    chip.classList.toggle("is-active", chip.dataset.filter === state.activeFilter);
  });
}

function createJobCard(job) {
  const node = elements.jobTemplate.content.firstElementChild.cloneNode(true);
  const title = node.querySelector(".job-title");
  const company = node.querySelector(".job-company");
  const companyStatusBadge = node.querySelector(".company-status-badge");
  const newBadge = node.querySelector(".new-badge");
  const sourceBadge = node.querySelector(".source-badge");
  const bandBadge = node.querySelector(".band-badge");
  const location = node.querySelector(".job-location");
  const salary = node.querySelector(".job-salary");
  const equity = node.querySelector(".job-equity");
  const companyStatus = node.querySelector(".job-company-status");
  const companySize = node.querySelector(".job-company-size");
  const benefitList = node.querySelector(".benefit-list");
  const recruiterValue = node.querySelector(".recruiter-value");
  const fitNote = node.querySelector(".fit-note");
  const applyLink = node.querySelector(".apply-link");
  const saveButton = node.querySelector(".save-button");
  const appliedButton = node.querySelector(".applied-button");

  title.textContent = job.title;
  company.textContent = job.company;
  companyStatusBadge.textContent = job.companyStatus === "public" ? "Public" : "Private";
  newBadge.hidden = !job.isNewToday;
  sourceBadge.textContent = job.source;
  bandBadge.textContent = job.salaryBandFit === "exact" ? "Exact band fit" : "Overlap fit";
  location.textContent = job.location;
  salary.textContent = job.salary;
  equity.textContent = job.equityStatus;
  companyStatus.textContent = job.companySharesNote;
  companySize.textContent = job.companySizeHint || "Not specified";
  fitNote.textContent = job.fitNote;
  applyLink.href = job.link;
  saveButton.textContent = job.shortlisted ? "Shortlisted" : "Save";
  saveButton.classList.toggle("is-saved", job.shortlisted);
  appliedButton.textContent = job.applied ? "Applied" : "Mark applied";
  appliedButton.classList.toggle("is-active", job.applied);

  benefitList.innerHTML = "";
  job.benefits.forEach((benefit) => {
    const item = document.createElement("li");
    item.textContent = benefit;
    benefitList.appendChild(item);
  });

  recruiterValue.textContent =
    formatRecruiter(job.recruiterName, job.recruiterContact) || "Not listed";

  saveButton.addEventListener("click", async () => {
    await updateJob(state.selectedDateKey, job.id, { shortlisted: !job.shortlisted });
    await refreshState();
    render();
  });

  appliedButton.addEventListener("click", async () => {
    await updateJob(state.selectedDateKey, job.id, { applied: !job.applied });
    await refreshState();
    render();
  });

  return node;
}

function formatRecruiter(name, contact) {
  if (name && contact) {
    return `${name} • ${contact}`;
  }
  return name || contact || "";
}

function getSelectedDigest() {
  return state.digestsByDate[state.selectedDateKey] || null;
}

function sortJobs(jobs) {
  return [...jobs].sort((left, right) => {
    if (left.companyStatus !== right.companyStatus) {
      return left.companyStatus === "public" ? -1 : 1;
    }
    if (left.shortlisted !== right.shortlisted) {
      return left.shortlisted ? -1 : 1;
    }
    return left.company.localeCompare(right.company);
  });
}

function applyFilter(jobs) {
  switch (state.activeFilter) {
    case "public":
      return jobs.filter((job) => job.companyStatus === "public");
    case "private":
      return jobs.filter((job) => job.companyStatus === "private");
    case "shortlisted":
      return jobs.filter((job) => job.shortlisted);
    case "active":
      return jobs.filter((job) => !job.applied);
    case "applied":
      return jobs.filter((job) => job.applied);
    default:
      return jobs;
  }
}

async function updateJob(dateKey, jobId, updates) {
  await fetch(`/api/jobs/${encodeURIComponent(dateKey)}/${encodeURIComponent(jobId)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
}

function renderCalendar() {
  const monthStart = state.visibleMonth;
  const gridStart = addDays(monthStart, -monthStart.getDay());
  const todayKey = getDateKey(new Date());

  elements.calendarMonthLabel.textContent = monthStart.toLocaleDateString(undefined, {
    month: "long",
    year: "numeric",
  });
  elements.calendarGrid.innerHTML = "";

  for (let index = 0; index < 42; index += 1) {
    const currentDate = addDays(gridStart, index);
    const dateKey = getDateKey(currentDate);
    const digest = state.digestsByDate[dateKey];
    const jobCount = digest?.jobs?.length || 0;
    const publicCount = digest?.jobs?.filter((job) => job.companyStatus === "public").length || 0;
    const button = document.createElement("button");

    button.type = "button";
    button.className = "calendar-day";
    button.classList.toggle("is-outside-month", currentDate.getMonth() !== monthStart.getMonth());
    button.classList.toggle("is-selected", dateKey === state.selectedDateKey);
    button.classList.toggle("is-today", dateKey === todayKey);
    button.innerHTML = `
      <span class="calendar-day-number">${currentDate.getDate()}</span>
      <span class="calendar-day-meta">${jobCount ? `${publicCount} public / ${jobCount} total` : "No digest"}</span>
    `;
    button.addEventListener("click", () => {
      state.selectedDateKey = dateKey;
      render();
    });
    elements.calendarGrid.appendChild(button);
  }
}

function changeVisibleMonth(offset) {
  state.visibleMonth = new Date(
    state.visibleMonth.getFullYear(),
    state.visibleMonth.getMonth() + offset,
    1
  );
  renderCalendar();
}

function jumpToToday() {
  state.selectedDateKey = getDateKey(new Date());
  state.visibleMonth = startOfMonth(new Date());
  render();
}

function syncSelectedDate() {
  if (!state.digestsByDate[state.selectedDateKey]) {
    const availableDates = Object.keys(state.digestsByDate).sort();
    state.selectedDateKey = availableDates.at(-1) || getDateKey(new Date());
  }
  state.visibleMonth = startOfMonth(new Date(`${state.selectedDateKey}T12:00:00`));
}

function getDateKey(date) {
  return date.toLocaleDateString("en-CA");
}

function formatDateLabel(dateKey) {
  return new Date(`${dateKey}T12:00:00`).toLocaleDateString(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
  });
}

function getRelativeDateLabel(dateKey) {
  const todayKey = getDateKey(new Date());
  const yesterdayKey = getDateKey(addDays(new Date(), -1));
  const tomorrowKey = getDateKey(addDays(new Date(), 1));

  if (dateKey === todayKey) {
    return "Today";
  }
  if (dateKey === yesterdayKey) {
    return "Yesterday";
  }
  if (dateKey === tomorrowKey) {
    return "Tomorrow";
  }
  return "Selected digest";
}

function addDays(date, days) {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
}

function startOfMonth(date) {
  return new Date(date.getFullYear(), date.getMonth(), 1);
}
