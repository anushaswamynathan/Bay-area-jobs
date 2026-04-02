const state = {
  searchPreferences: {},
  criteria: {},
  digestsByDate: {},
  selectedDateKey: getDateKey(new Date()),
  visibleMonth: startOfMonth(new Date()),
  activeFilter: "all",
  criteriaPanelOpen: false,
  calendarPanelOpen: false,
  isRefreshing: false,
  refreshStatus: null,
  refreshPollTimer: null,
  sourceHealth: null,
  currentPage: 1,
  recommendedPageSize: 24,
  companyFilter: "",
};

const elements = {
  activeDateCaption: document.querySelector("#active-date-caption"),
  todayLabel: document.querySelector("#today-label"),
  digestSummary: document.querySelector("#digest-summary"),
  refreshStatus: document.querySelector("#refresh-status"),
  sourceHealthList: document.querySelector("#source-health-list"),
  recommendedPagination: document.querySelector("#recommended-pagination"),
  previousPage: document.querySelector("#previous-page"),
  nextPage: document.querySelector("#next-page"),
  paginationLabel: document.querySelector("#pagination-label"),
  companyFilterInput: document.querySelector("#company-filter-input"),
  companyFilterChips: document.querySelector("#company-filter-chips"),
  heroTitle: document.querySelector("#hero-title"),
  heroCopy: document.querySelector("#hero-copy"),
  resultsTitle: document.querySelector("#results-title"),
  criteriaPanel: document.querySelector("#criteria-panel"),
  calendarPanel: document.querySelector("#calendar-panel"),
  recommendedCount: document.querySelector("#recommended-count"),
  appliedCount: document.querySelector("#applied-count"),
  notInterestedCount: document.querySelector("#not-interested-count"),
  openImportDialog: document.querySelector("#open-import-dialog"),
  toggleCriteria: document.querySelector("#toggle-criteria"),
  toggleCalendar: document.querySelector("#toggle-calendar"),
  searchForm: document.querySelector("#search-form"),
  roleNameInput: document.querySelector("#role-name-input"),
  cityInput: document.querySelector("#city-input"),
  stateInput: document.querySelector("#state-input"),
  compMinInput: document.querySelector("#comp-min-input"),
  compMaxInput: document.querySelector("#comp-max-input"),
  resultLimitInput: document.querySelector("#result-limit-input"),
  importDialog: document.querySelector("#import-dialog"),
  importForm: document.querySelector("#import-form"),
  closeImportDialog: document.querySelector("#close-import-dialog"),
  importDateInput: document.querySelector("#import-date-input"),
  importJsonInput: document.querySelector("#import-json-input"),
  importStatus: document.querySelector("#import-status"),
  recommendedSection: document.querySelector("#recommended-section"),
  appliedSection: document.querySelector("#applied-section"),
  notInterestedSection: document.querySelector("#not-interested-section"),
  recommendedJobList: document.querySelector("#recommended-job-list"),
  appliedJobList: document.querySelector("#applied-job-list"),
  notInterestedJobList: document.querySelector("#not-interested-job-list"),
  recommendedGroupTitle: document.querySelector("#recommended-group-title"),
  recommendedGroupCopy: document.querySelector("#recommended-group-copy"),
  appliedGroupTitle: document.querySelector("#applied-group-title"),
  notInterestedGroupTitle: document.querySelector("#not-interested-group-title"),
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
  await refreshRefreshStatus();
  await refreshSourceHealth();
  syncSelectedDate();
  render();
  wireEvents();
  syncRefreshPolling();
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
  elements.searchForm.addEventListener("submit", handleSearchSave);
  elements.filterChips.forEach((chip) => {
    chip.addEventListener("click", () => {
      state.activeFilter = chip.dataset.filter;
      state.currentPage = 1;
      render();
    });
  });
  elements.companyFilterInput.addEventListener("input", () => {
    state.companyFilter = elements.companyFilterInput.value.trim().toLowerCase();
    state.currentPage = 1;
    render();
  });
  elements.previousPage.addEventListener("click", () => {
    state.currentPage = Math.max(1, state.currentPage - 1);
    render();
  });
  elements.nextPage.addEventListener("click", () => {
    state.currentPage += 1;
    render();
  });
}

async function refreshState() {
  const response = await fetch("/api/state");
  const payload = await response.json();
  state.searchPreferences = payload.searchPreferences || {};
  state.criteria = payload.criteria || {};
  state.digestsByDate = payload.digestsByDate || {};
}

async function refreshRefreshStatus() {
  const response = await fetch("/api/refresh-status");
  state.refreshStatus = await response.json();
}

async function refreshSourceHealth() {
  const response = await fetch("/api/source-health");
  state.sourceHealth = await response.json();
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

async function handleSearchSave(event) {
  event.preventDefault();
  const payload = {
    roleName: elements.roleNameInput.value.trim(),
    city: elements.cityInput.value.trim(),
    state: elements.stateInput.value.trim(),
    compMin: Number(elements.compMinInput.value),
    compMax: Number(elements.compMaxInput.value),
    resultLimit: Number(elements.resultLimitInput.value),
  };
  state.isRefreshing = true;
  elements.toggleCriteria.disabled = true;
  elements.toggleCalendar.disabled = true;
  await fetch("/api/search-preferences", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  try {
    const refreshResponse = await fetch("/api/refresh-digest", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    if (!refreshResponse.ok) {
      throw new Error("Refresh failed");
    }
    await refreshRefreshStatus();
    await refreshSourceHealth();
    syncRefreshPolling();
    state.criteriaPanelOpen = false;
    render();
    renderUtilityPanels();
  } catch (error) {
    await refreshState();
    await refreshRefreshStatus();
    await refreshSourceHealth();
    render();
    window.alert("The search criteria were saved, but the refresh did not complete. Please try again in a moment.");
  } finally {
    elements.toggleCriteria.disabled = false;
    elements.toggleCalendar.disabled = false;
  }
}

function openImportDialog() {
  const selectedDigest = getSelectedDigest();
  elements.importDateInput.value = state.selectedDateKey;
  elements.importJsonInput.value = JSON.stringify(
    {
      date: state.selectedDateKey,
      searchPreferences: state.searchPreferences,
      summary: selectedDigest?.summary || "Fresh daily digest",
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
  payload.searchPreferences = payload.searchPreferences || state.searchPreferences;

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
  const recommendedJobs = applyCompanyFilter(applyViewFilter(allJobs.filter((job) => !job.applied && !job.notInterested)));
  const appliedJobs = applyCompanyFilter(applyViewFilter(allJobs.filter((job) => job.applied)));
  const notInterestedJobs = applyCompanyFilter(applyViewFilter(allJobs.filter((job) => job.notInterested)));
  const visibleGroupsCount = recommendedJobs.length + appliedJobs.length + notInterestedJobs.length;

  elements.activeDateCaption.textContent = getRelativeDateLabel(state.selectedDateKey);
  elements.todayLabel.textContent = formatDateLabel(state.selectedDateKey);
  elements.digestSummary.textContent = digest?.summary || "No digest is available for this date yet.";
  elements.recommendedCount.textContent = String(allJobs.filter((job) => !job.applied && !job.notInterested).length);
  elements.appliedCount.textContent = String(allJobs.filter((job) => job.applied).length);
  elements.notInterestedCount.textContent = String(allJobs.filter((job) => job.notInterested).length);
  elements.emptyState.hidden = visibleGroupsCount > 0;

  renderDynamicText();
  renderRefreshStatus();
  renderSourceHealth();
  renderCompanyFilter(allJobs);
  renderSearchForm();
  renderFilterState();
  renderUtilityPanels();
  renderGroups(recommendedJobs, appliedJobs, notInterestedJobs);
  renderCalendar();
}

function renderDynamicText() {
  const prefs = state.searchPreferences;
  const locationLabel = formatLocation(prefs.city, prefs.state);
  const digest = getSelectedDigest();
  const jobs = sortJobs(digest?.jobs || []);
  const recommendedCount = jobs.filter((job) => !job.applied && !job.notInterested).length;
  elements.heroTitle.textContent = `${prefs.roleName || "Product roles"} in ${locationLabel}`;
  if (state.isRefreshing || state.refreshStatus?.state === "running") {
    elements.heroCopy.textContent = `Updating ${prefs.roleName || "your search"} results in the background. You can keep browsing while the next digest loads.`;
  } else {
    elements.heroCopy.textContent = `Tracking up to ${prefs.resultLimit || 50} daily roles within 50 miles of ${locationLabel}, with base comp between ${formatCurrency(prefs.compMin)} and ${formatCurrency(prefs.compMax)}.`;
  }
  elements.resultsTitle.textContent = `${recommendedCount} recommended roles for ${locationLabel}`;
  document.title = `${prefs.roleName || "Product Manager"} Jobs | ${locationLabel}`;
}

function renderRefreshStatus() {
  const refresh = state.refreshStatus;
  if (!refresh || refresh.state === "idle") {
    elements.refreshStatus.hidden = true;
    elements.refreshStatus.textContent = "";
    return;
  }

  elements.refreshStatus.hidden = false;
  elements.refreshStatus.classList.toggle("is-error", refresh.state === "failed");
  elements.refreshStatus.classList.toggle("is-success", refresh.state === "completed");

  if (refresh.state === "running") {
    elements.refreshStatus.textContent = refresh.message || "Refreshing live job sources...";
    return;
  }
  if (refresh.state === "completed") {
    elements.refreshStatus.textContent = `${refresh.message || "Refresh complete."} Loaded ${refresh.jobCount || 0} jobs.`;
    return;
  }
  elements.refreshStatus.textContent = refresh.error || refresh.message || "Refresh failed.";
}

function renderSourceHealth() {
  elements.sourceHealthList.innerHTML = "";
  const health = state.sourceHealth;
  if (!health?.ok) {
    elements.sourceHealthList.innerHTML = '<p class="empty-state">Source health will appear after the next refresh.</p>';
    return;
  }
  const entries = Object.entries(health.sources || {})
    .sort((left, right) => right[1].fetched - left[1].fetched || left[0].localeCompare(right[0]))
    .slice(0, 12);
  for (const [name, info] of entries) {
    const card = document.createElement("article");
    card.className = "source-health-card";
    const tone = info.error ? "error" : info.fetched > 0 ? "healthy" : "weak";
    card.innerHTML = `
      <div class="source-health-top">
        <h3>${name}</h3>
        <span class="source-health-badge is-${tone}">${info.error ? "Error" : info.fetched > 0 ? "Active" : "No matches"}</span>
      </div>
      <p class="source-health-meta">${info.matched || 0} matched of ${info.fetched || 0} fetched${info.previewFetched ? ` • ${info.previewFetched} in preview` : ""}</p>
      <p class="source-health-meta">${info.error || "Latest refresh completed without a source error."}</p>
    `;
    elements.sourceHealthList.appendChild(card);
  }
}

function renderCompanyFilter(allJobs) {
  elements.companyFilterInput.value = state.companyFilter;
  elements.companyFilterChips.innerHTML = "";
  const companies = [...new Set(allJobs.map((job) => job.company).filter(Boolean))].sort().slice(0, 10);
  for (const company of companies) {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "filter-chip";
    chip.textContent = company;
    chip.classList.toggle("is-active", state.companyFilter === company.toLowerCase());
    chip.addEventListener("click", () => {
      const nextValue = state.companyFilter === company.toLowerCase() ? "" : company.toLowerCase();
      state.companyFilter = nextValue;
      elements.companyFilterInput.value = nextValue;
      state.currentPage = 1;
      render();
    });
    elements.companyFilterChips.appendChild(chip);
  }
}

function renderSearchForm() {
  const prefs = state.searchPreferences;
  elements.roleNameInput.value = prefs.roleName || "";
  elements.cityInput.value = prefs.city || "";
  elements.stateInput.value = prefs.state || "";
  elements.compMinInput.value = prefs.compMin || "";
  elements.compMaxInput.value = prefs.compMax || "";
  elements.resultLimitInput.value = prefs.resultLimit || "";
}

function renderUtilityPanels() {
  elements.criteriaPanel.hidden = !state.criteriaPanelOpen;
  elements.calendarPanel.hidden = !state.calendarPanelOpen;
  elements.toggleCriteria.classList.toggle("is-active", state.criteriaPanelOpen);
  elements.toggleCalendar.classList.toggle("is-active", state.calendarPanelOpen);
}

function renderFilterState() {
  elements.filterChips.forEach((chip) => {
    chip.classList.toggle("is-active", chip.dataset.filter === state.activeFilter);
  });
}

function renderGroups(recommendedJobs, appliedJobs, notInterestedJobs) {
  elements.recommendedJobList.innerHTML = "";
  elements.appliedJobList.innerHTML = "";
  elements.notInterestedJobList.innerHTML = "";

  elements.recommendedSection.hidden = !["all", "recommended", "public", "private"].includes(state.activeFilter) && state.activeFilter !== "all";
  elements.appliedSection.hidden = !["all", "applied", "public", "private"].includes(state.activeFilter) && state.activeFilter !== "all";
  elements.notInterestedSection.hidden = !["all", "not-interested", "public", "private"].includes(state.activeFilter) && state.activeFilter !== "all";

  const exactCount = recommendedJobs.filter((job) => job.salaryBandFit === "exact").length;
  const nearCount = recommendedJobs.length - exactCount;
  const totalPages = Math.max(1, Math.ceil(recommendedJobs.length / state.recommendedPageSize));
  state.currentPage = Math.min(state.currentPage, totalPages);
  const startIndex = (state.currentPage - 1) * state.recommendedPageSize;
  const pagedRecommendedJobs = recommendedJobs.slice(startIndex, startIndex + state.recommendedPageSize);

  elements.recommendedGroupTitle.textContent = `Fresh roles to review (${recommendedJobs.length})`;
  elements.recommendedGroupCopy.textContent = `${exactCount} exact fit${exactCount === 1 ? "" : "s"} and ${nearCount} near match${nearCount === 1 ? "" : "es"}. Applied and not interested jobs are excluded automatically.`;
  elements.appliedGroupTitle.textContent = `Already submitted (${appliedJobs.length})`;
  elements.notInterestedGroupTitle.textContent = `Hidden from your recommendations (${notInterestedJobs.length})`;

  pagedRecommendedJobs.forEach((job) => elements.recommendedJobList.appendChild(createJobCard(job)));
  appliedJobs.forEach((job) => elements.appliedJobList.appendChild(createJobCard(job)));
  notInterestedJobs.forEach((job) => elements.notInterestedJobList.appendChild(createJobCard(job)));
  elements.recommendedPagination.hidden = recommendedJobs.length <= state.recommendedPageSize || state.activeFilter === "applied" || state.activeFilter === "not-interested";
  elements.paginationLabel.textContent = `Page ${state.currentPage} of ${totalPages}`;
  elements.previousPage.disabled = state.currentPage <= 1;
  elements.nextPage.disabled = state.currentPage >= totalPages;

  if (state.activeFilter === "applied") {
    elements.recommendedSection.hidden = true;
    elements.notInterestedSection.hidden = true;
  }
  if (state.activeFilter === "not-interested") {
    elements.recommendedSection.hidden = true;
    elements.appliedSection.hidden = true;
  }
  if (state.activeFilter === "recommended") {
    elements.appliedSection.hidden = true;
    elements.notInterestedSection.hidden = true;
  }
}

function applyCompanyFilter(jobs) {
  if (!state.companyFilter) {
    return jobs;
  }
  return jobs.filter((job) => (job.company || "").toLowerCase().includes(state.companyFilter));
}

function createJobCard(job) {
  const node = elements.jobTemplate.content.firstElementChild.cloneNode(true);
  node.querySelector(".job-title").textContent = job.title;
  node.querySelector(".job-company").textContent = job.company;
  node.querySelector(".company-status-badge").textContent =
    job.companyStatus === "public" ? "Public" : "Private";

  const repeatBadge = node.querySelector(".repeat-badge");
  if (job.shownYesterday) {
    repeatBadge.hidden = false;
    repeatBadge.textContent = "Shown yesterday";
  } else if (job.seenBefore) {
    repeatBadge.hidden = false;
    repeatBadge.textContent = "Seen before";
  }

  node.querySelector(".new-badge").hidden = !job.isNewToday;
  node.querySelector(".source-badge").textContent = job.source;
  node.querySelector(".band-badge").textContent = job.salaryBandFit === "exact" ? "Exact fit" : "Near match";
  node.querySelector(".job-location").textContent = job.location || "Not listed";
  node.querySelector(".job-salary").textContent = job.salary || "Not listed";
  node.querySelector(".job-equity").textContent = job.equityStatus || "Not listed";
  node.querySelector(".job-company-status").textContent = job.companySharesNote || "Not listed";
  node.querySelector(".job-company-size").textContent = job.companySizeHint || "Not specified";
  node.querySelector(".fit-note").textContent = job.fitNote || "No fit note available.";
  node.querySelector(".recruiter-value").textContent =
    formatRecruiter(job.recruiterName, job.recruiterContact) || "Not listed";

  const benefitList = node.querySelector(".benefit-list");
  benefitList.innerHTML = "";
  (job.benefits || []).forEach((benefit) => {
    const item = document.createElement("li");
    item.textContent = benefit;
    benefitList.appendChild(item);
  });
  if (!job.benefits || !job.benefits.length) {
    const item = document.createElement("li");
    item.textContent = "Benefits not listed";
    benefitList.appendChild(item);
  }

  const applyLink = node.querySelector(".apply-link");
  applyLink.href = job.link;

  const saveButton = node.querySelector(".save-button");
  saveButton.textContent = job.shortlisted ? "Saved" : "Save";
  saveButton.classList.toggle("is-saved", job.shortlisted);
  saveButton.addEventListener("click", async () => {
    await updateJob(state.selectedDateKey, job.id, { shortlisted: !job.shortlisted });
    await refreshState();
    render();
  });

  const appliedButton = node.querySelector(".applied-button");
  appliedButton.textContent = job.applied ? "Applied" : "Mark applied";
  appliedButton.classList.toggle("is-active", job.applied);
  appliedButton.addEventListener("click", async () => {
    await updateJob(state.selectedDateKey, job.id, { applied: !job.applied });
    await refreshState();
    render();
  });

  const notInterestedButton = node.querySelector(".not-interested-button");
  notInterestedButton.textContent = job.notInterested ? "Not interested" : "Mark not interested";
  notInterestedButton.classList.toggle("is-active", job.notInterested);
  notInterestedButton.addEventListener("click", async () => {
    await updateJob(state.selectedDateKey, job.id, { notInterested: !job.notInterested });
    await refreshState();
    render();
  });

  return node;
}

function applyViewFilter(jobs) {
  switch (state.activeFilter) {
    case "public":
      return jobs.filter((job) => job.companyStatus === "public");
    case "private":
      return jobs.filter((job) => job.companyStatus === "private");
    case "applied":
      return jobs.filter((job) => job.applied);
    case "not-interested":
      return jobs.filter((job) => job.notInterested);
    case "recommended":
      return jobs.filter((job) => !job.applied && !job.notInterested);
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
    if (left.applied !== right.applied) {
      return left.applied ? 1 : -1;
    }
    if (left.notInterested !== right.notInterested) {
      return left.notInterested ? 1 : -1;
    }
    if (left.companyStatus !== right.companyStatus) {
      return left.companyStatus === "public" ? -1 : 1;
    }
    if (left.shownYesterday !== right.shownYesterday) {
      return left.shownYesterday ? 1 : -1;
    }
    return left.company.localeCompare(right.company) || left.title.localeCompare(right.title);
  });
}

function renderCalendar() {
  const monthStart = state.visibleMonth;
  const gridStart = addDays(monthStart, -monthStart.getDay());
  const today = getDateKey(new Date());
  elements.calendarMonthLabel.textContent = monthStart.toLocaleDateString(undefined, {
    month: "long",
    year: "numeric",
  });
  elements.calendarGrid.innerHTML = "";

  for (let index = 0; index < 42; index += 1) {
    const currentDate = addDays(gridStart, index);
    const dateKey = getDateKey(currentDate);
    const digest = state.digestsByDate[dateKey];
    const jobs = digest?.jobs || [];
    const button = document.createElement("button");
    button.type = "button";
    button.className = "calendar-day";
    button.classList.toggle("is-outside-month", currentDate.getMonth() !== monthStart.getMonth());
    button.classList.toggle("is-selected", dateKey === state.selectedDateKey);
    button.classList.toggle("is-today", dateKey === today);
    button.innerHTML = `
      <span class="calendar-day-number">${currentDate.getDate()}</span>
      <span class="calendar-day-meta">${jobs.length ? `${jobs.filter((job) => !job.applied && !job.notInterested).length} recommended` : "No digest"}</span>
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
    state.selectedDateKey = getLatestDigestDate();
  }
  state.visibleMonth = startOfMonth(new Date(`${state.selectedDateKey}T12:00:00`));
}

function getLatestDigestDate() {
  const availableDates = Object.keys(state.digestsByDate).sort();
  return availableDates.at(-1) || getDateKey(new Date());
}

function syncRefreshPolling() {
  if (state.refreshPollTimer) {
    window.clearInterval(state.refreshPollTimer);
    state.refreshPollTimer = null;
  }
  if (!state.refreshStatus || state.refreshStatus.state !== "running") {
    state.isRefreshing = false;
    return;
  }
  state.isRefreshing = true;
  state.refreshPollTimer = window.setInterval(async () => {
    await refreshRefreshStatus();
    if (state.refreshStatus?.state === "running") {
      await refreshState();
      state.selectedDateKey = getLatestDigestDate();
      state.visibleMonth = startOfMonth(new Date(`${state.selectedDateKey}T12:00:00`));
      await refreshSourceHealth();
      render();
      return;
    }
    await refreshState();
    await refreshSourceHealth();
    state.selectedDateKey = getLatestDigestDate();
    state.visibleMonth = startOfMonth(new Date(`${state.selectedDateKey}T12:00:00`));
    state.isRefreshing = false;
    syncRefreshPolling();
    render();
  }, 2500);
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

function formatCurrency(value) {
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(Number(value || 0));
}

function formatLocation(city, stateName) {
  return [city, stateName].filter(Boolean).join(", ") || "your target market";
}
