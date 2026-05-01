const state = {
  masterData: {
    teachers: [{ name: "王老師", salary: 550 }],
    grades: ["小六", "國一", "國二", "高一"],
    subjects: ["數學", "英文", "自然"],
    hourlyRates: [{ name: "一般班", value: 700 }, { name: "衝刺班", value: 850 }]
  },
  schedules: [],
  skipDates: [],
  makeupDates: []
};

const weekdayMap = ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"];

const dom = {
  masterImportFile: document.getElementById("masterImportFile"),
  importMasterBtn: document.getElementById("importMasterBtn"),
  resetMasterBtn: document.getElementById("resetMasterBtn"),
  teacherNameInput: document.getElementById("teacherNameInput"),
  teacherSalaryInput: document.getElementById("teacherSalaryInput"),
  addTeacherBtn: document.getElementById("addTeacherBtn"),
  gradeInput: document.getElementById("gradeInput"),
  addGradeBtn: document.getElementById("addGradeBtn"),
  subjectInput: document.getElementById("subjectInput"),
  addSubjectBtn: document.getElementById("addSubjectBtn"),
  rateNameInput: document.getElementById("rateNameInput"),
  rateValueInput: document.getElementById("rateValueInput"),
  addRateBtn: document.getElementById("addRateBtn"),
  teacherList: document.getElementById("teacherList"),
  gradeList: document.getElementById("gradeList"),
  subjectList: document.getElementById("subjectList"),
  rateList: document.getElementById("rateList"),
  scheduleForm: document.getElementById("scheduleForm"),
  teacherSelect: document.getElementById("teacherSelect"),
  studentName: document.getElementById("studentName"),
  gradeSelect: document.getElementById("gradeSelect"),
  subjectSelect: document.getElementById("subjectSelect"),
  firstClassDate: document.getElementById("firstClassDate"),
  weekdayDisplay: document.getElementById("weekdayDisplay"),
  recurrence: document.getElementById("recurrence"),
  durationMonths: document.getElementById("durationMonths"),
  startTime: document.getElementById("startTime"),
  endTime: document.getElementById("endTime"),
  classHours: document.getElementById("classHours"),
  hourlyRateTypeSelect: document.getElementById("hourlyRateTypeSelect"),
  tuitionHourlyRate: document.getElementById("tuitionHourlyRate"),
  teacherHourlySalary: document.getElementById("teacherHourlySalary"),
  skipDateInput: document.getElementById("skipDateInput"),
  addSkipDateBtn: document.getElementById("addSkipDateBtn"),
  makeupDateInput: document.getElementById("makeupDateInput"),
  addMakeupDateBtn: document.getElementById("addMakeupDateBtn"),
  skipDateList: document.getElementById("skipDateList"),
  makeupDateList: document.getElementById("makeupDateList"),
  exportExcelBtn: document.getElementById("exportExcelBtn"),
  clearSchedulesBtn: document.getElementById("clearSchedulesBtn"),
  summaryCards: document.getElementById("summaryCards"),
  monthlySummary: document.getElementById("monthlySummary"),
  scheduleTableWrap: document.getElementById("scheduleTableWrap"),
  toast: document.getElementById("toast")
};

function saveState() {
  localStorage.setItem("flyingYouthSchedulingState", JSON.stringify(state));
}

function loadState() {
  const raw = localStorage.getItem("flyingYouthSchedulingState");
  if (!raw) {
    fillDurationOptions();
    renderAll();
    return;
  }

  try {
    const parsed = JSON.parse(raw);
    if (parsed.masterData) {
      state.masterData = parsed.masterData;
    }
    state.schedules = Array.isArray(parsed.schedules) ? parsed.schedules : [];
    state.skipDates = Array.isArray(parsed.skipDates) ? parsed.skipDates : [];
    state.makeupDates = Array.isArray(parsed.makeupDates) ? parsed.makeupDates : [];
  } catch (error) {
    console.error("無法讀取儲存資料", error);
  }

  fillDurationOptions();
  renderAll();
}

function fillDurationOptions() {
  dom.durationMonths.innerHTML = "";
  for (let i = 1; i <= 12; i += 1) {
    const option = document.createElement("option");
    option.value = String(i);
    option.textContent = `${i} 個月`;
    dom.durationMonths.append(option);
  }
}

function renderAll() {
  renderMasterLists();
  renderSelectOptions();
  renderExceptionLists();
  renderScheduleResult();
}

function renderMasterLists() {
  renderList(
    dom.teacherList,
    state.masterData.teachers,
    (item) => `${item.name}（時薪 ${formatCurrency(item.salary)}）`,
    (_item, index) => {
      state.masterData.teachers.splice(index, 1);
      renderAll();
      saveState();
    }
  );

  renderList(dom.gradeList, state.masterData.grades, (item) => item, (_item, index) => {
    state.masterData.grades.splice(index, 1);
    renderAll();
    saveState();
  });

  renderList(dom.subjectList, state.masterData.subjects, (item) => item, (_item, index) => {
    state.masterData.subjects.splice(index, 1);
    renderAll();
    saveState();
  });

  renderList(
    dom.rateList,
    state.masterData.hourlyRates,
    (item) => `${item.name}（${formatCurrency(item.value)}/hr）`,
    (_item, index) => {
      state.masterData.hourlyRates.splice(index, 1);
      renderAll();
      saveState();
    }
  );
}

function renderList(container, items, labelBuilder, onDelete) {
  container.innerHTML = "";
  if (items.length === 0) {
    const li = document.createElement("li");
    li.textContent = "尚無資料";
    container.append(li);
    return;
  }
  items.forEach((item, index) => {
    const li = document.createElement("li");
    const span = document.createElement("span");
    span.textContent = labelBuilder(item);
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = "刪除";
    btn.className = "remove-btn";
    btn.addEventListener("click", () => onDelete(item, index));
    li.append(span, btn);
    container.append(li);
  });
}

function renderSelectOptions() {
  populateSelect(dom.teacherSelect, state.masterData.teachers.map((t) => t.name), true);
  populateSelect(dom.gradeSelect, state.masterData.grades, true);
  populateSelect(dom.subjectSelect, state.masterData.subjects, true);
  populateSelect(dom.hourlyRateTypeSelect, state.masterData.hourlyRates.map((r) => r.name), false);

  const firstRate = state.masterData.hourlyRates[0];
  if (firstRate && !dom.tuitionHourlyRate.value) {
    dom.tuitionHourlyRate.value = String(firstRate.value);
  }

  const selectedTeacher = state.masterData.teachers.find((t) => t.name === dom.teacherSelect.value);
  if (selectedTeacher && !dom.teacherHourlySalary.value) {
    dom.teacherHourlySalary.value = String(selectedTeacher.salary);
  }
}

function populateSelect(select, values, withPlaceholder) {
  const currentValue = select.value;
  select.innerHTML = "";
  if (withPlaceholder) {
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "請選擇";
    select.append(placeholder);
  }
  values.forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    select.append(option);
  });

  if (values.includes(currentValue)) {
    select.value = currentValue;
  } else if (withPlaceholder) {
    select.value = "";
  } else if (values.length > 0) {
    select.value = values[0];
  }
}

function renderExceptionLists() {
  renderDateTagList(dom.skipDateList, state.skipDates, (date, idx) => {
    state.skipDates.splice(idx, 1);
    renderExceptionLists();
    saveState();
  });

  renderDateTagList(dom.makeupDateList, state.makeupDates, (date, idx) => {
    state.makeupDates.splice(idx, 1);
    renderExceptionLists();
    saveState();
  });
}

function renderDateTagList(container, values, onDelete) {
  container.innerHTML = "";
  if (values.length === 0) {
    const li = document.createElement("li");
    li.textContent = "尚未設定";
    container.append(li);
    return;
  }
  values.forEach((value, idx) => {
    const li = document.createElement("li");
    const text = document.createElement("span");
    text.textContent = `${value}（${getWeekdayText(value)}）`;
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = "移除";
    btn.className = "remove-btn";
    btn.addEventListener("click", () => onDelete(value, idx));
    li.append(text, btn);
    container.append(li);
  });
}

function getWeekdayText(dateStr) {
  const date = new Date(`${dateStr}T00:00:00`);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  return weekdayMap[date.getDay()];
}

function updateWeekdayDisplay() {
  dom.weekdayDisplay.value = getWeekdayText(dom.firstClassDate.value);
}

function updateClassHours() {
  const start = dom.startTime.value;
  const end = dom.endTime.value;
  if (!start || !end) {
    dom.classHours.value = "";
    return;
  }
  const hours = calcHourDuration(start, end);
  if (hours <= 0) {
    dom.classHours.value = "時間錯誤";
    return;
  }
  dom.classHours.value = `${hours.toFixed(2)} 小時`;
}

function calcHourDuration(startTime, endTime) {
  const [startHour, startMinute] = startTime.split(":").map(Number);
  const [endHour, endMinute] = endTime.split(":").map(Number);
  const startMinutes = startHour * 60 + startMinute;
  const endMinutes = endHour * 60 + endMinute;
  return (endMinutes - startMinutes) / 60;
}

function handleRateTypeChange() {
  const selected = state.masterData.hourlyRates.find((r) => r.name === dom.hourlyRateTypeSelect.value);
  if (selected) {
    dom.tuitionHourlyRate.value = String(selected.value);
  }
}

function handleTeacherChange() {
  const selected = state.masterData.teachers.find((teacher) => teacher.name === dom.teacherSelect.value);
  if (selected) {
    dom.teacherHourlySalary.value = String(selected.salary);
  }
}

function sortDateStrings(values) {
  return values.slice().sort((a, b) => (a > b ? 1 : -1));
}

function addExceptionDate(type) {
  const input = type === "skip" ? dom.skipDateInput : dom.makeupDateInput;
  const value = input.value;
  if (!value) {
    showToast("請先選擇日期");
    return;
  }

  if (type === "skip") {
    if (state.skipDates.includes(value)) {
      showToast("停課日期已存在");
      return;
    }
    state.skipDates = sortDateStrings([...state.skipDates, value]);
  } else {
    if (state.makeupDates.includes(value)) {
      showToast("補課日期已存在");
      return;
    }
    state.makeupDates = sortDateStrings([...state.makeupDates, value]);
  }

  input.value = "";
  renderExceptionLists();
  saveState();
}

function generateScheduleRows(payload) {
  const {
    teacherName,
    studentName,
    grade,
    subject,
    firstDate,
    recurrence,
    durationMonths,
    startTime,
    endTime,
    classHours,
    tuitionHourlyRate,
    teacherHourlySalary
  } = payload;

  const allDates = [];
  let current = new Date(`${firstDate}T00:00:00`);
  const endDate = new Date(`${firstDate}T00:00:00`);
  endDate.setMonth(endDate.getMonth() + durationMonths);

  while (current <= endDate) {
    const dateStr = formatDate(current);
    allDates.push({ date: dateStr, isMakeup: false, source: "regular" });
    if (recurrence === "weekly") {
      current.setDate(current.getDate() + 7);
    } else {
      current.setMonth(current.getMonth() + 1);
    }
  }

  state.makeupDates.forEach((dateStr) => {
    const date = new Date(`${dateStr}T00:00:00`);
    if (date >= new Date(`${firstDate}T00:00:00`) && date <= endDate) {
      allDates.push({ date: dateStr, isMakeup: true, source: "makeup" });
    }
  });

  const finalDates = allDates
    .filter((item) => item.isMakeup || !state.skipDates.includes(item.date))
    .sort((a, b) => (a.date > b.date ? 1 : -1));

  return finalDates.map((item, idx) => {
    const classFee = classHours * tuitionHourlyRate;
    const classCost = classHours * teacherHourlySalary;
    return {
      id: `CLS-${Date.now()}-${idx + 1}`,
      teacherName,
      studentName,
      grade,
      subject,
      classDate: item.date,
      weekday: getWeekdayText(item.date),
      recurrence,
      durationMonths,
      startTime,
      endTime,
      classHours,
      tuitionHourlyRate,
      teacherHourlySalary,
      classFee,
      classCost,
      type: item.isMakeup ? "補課" : "一般課"
    };
  });
}

function formatDate(date) {
  const yyyy = date.getFullYear();
  const mm = String(date.getMonth() + 1).padStart(2, "0");
  const dd = String(date.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

function formatCurrency(value) {
  return Number(value || 0).toLocaleString("zh-TW", { maximumFractionDigits: 2 });
}

function handleCreateSchedule(event) {
  event.preventDefault();

  const classHours = calcHourDuration(dom.startTime.value, dom.endTime.value);
  if (classHours <= 0) {
    showToast("下課時間必須晚於上課時間");
    return;
  }
  if (!dom.teacherSelect.value || !dom.gradeSelect.value || !dom.subjectSelect.value) {
    showToast("請補齊老師、年級、科目");
    return;
  }

  const payload = {
    teacherName: dom.teacherSelect.value,
    studentName: dom.studentName.value.trim(),
    grade: dom.gradeSelect.value,
    subject: dom.subjectSelect.value,
    firstDate: dom.firstClassDate.value,
    recurrence: dom.recurrence.value,
    durationMonths: Number(dom.durationMonths.value),
    startTime: dom.startTime.value,
    endTime: dom.endTime.value,
    classHours,
    tuitionHourlyRate: Number(dom.tuitionHourlyRate.value),
    teacherHourlySalary: Number(dom.teacherHourlySalary.value)
  };

  if (!payload.studentName || !payload.firstDate) {
    showToast("請補齊學生姓名與上課日期");
    return;
  }

  const rows = generateScheduleRows(payload);
  if (rows.length === 0) {
    showToast("此條件下無可排課日期，請檢查停課/補課設定");
    return;
  }

  state.schedules.push(...rows);
  renderScheduleResult();
  saveState();
  dom.scheduleForm.reset();
  updateClassHours();
  updateWeekdayDisplay();
  showToast(`已建立 ${rows.length} 筆排課資料`);
}

function buildMonthlySummary() {
  const map = new Map();
  state.schedules.forEach((item) => {
    const month = item.classDate.slice(0, 7);
    if (!map.has(month)) {
      map.set(month, {
        month,
        classes: 0,
        hours: 0,
        monthlyFee: 0,
        monthlyCost: 0
      });
    }
    const row = map.get(month);
    row.classes += 1;
    row.hours += Number(item.classHours);
    row.monthlyFee += Number(item.classFee);
    row.monthlyCost += Number(item.classCost);
  });
  return Array.from(map.values()).sort((a, b) => (a.month > b.month ? 1 : -1));
}

function calculateSummary() {
  const totalHours = state.schedules.reduce((acc, row) => acc + Number(row.classHours), 0);
  const totalFee = state.schedules.reduce((acc, row) => acc + Number(row.classFee), 0);
  const totalCost = state.schedules.reduce((acc, row) => acc + Number(row.classCost), 0);
  return {
    classes: state.schedules.length,
    totalHours,
    totalFee,
    totalCost,
    grossProfit: totalFee - totalCost
  };
}

function renderScheduleResult() {
  const summary = calculateSummary();
  dom.summaryCards.innerHTML = [
    { key: "排課堂數", value: `${summary.classes} 堂` },
    { key: "總時數", value: `${summary.totalHours.toFixed(2)} 小時` },
    { key: "每次收費總計", value: `${formatCurrency(summary.totalFee)}` },
    { key: "總成本", value: `${formatCurrency(summary.totalCost)}` },
    { key: "毛利", value: `${formatCurrency(summary.grossProfit)}` }
  ]
    .map(
      (item) => `<div class="summary-card"><h3>${item.key}</h3><p>${item.value}</p></div>`
    )
    .join("");

  renderMonthlySummaryTable();
  renderScheduleTable();
}

function renderMonthlySummaryTable() {
  const rows = buildMonthlySummary();
  if (rows.length === 0) {
    dom.monthlySummary.innerHTML = "<p>目前尚無月份費用資料。</p>";
    return;
  }
  const html = `
    <table>
      <thead>
        <tr>
          <th>月份</th>
          <th>堂數</th>
          <th>總時數</th>
          <th>每月費用</th>
          <th>每月成本</th>
          <th>每月毛利</th>
        </tr>
      </thead>
      <tbody>
        ${rows
          .map(
            (row) => `
              <tr>
                <td>${row.month}</td>
                <td>${row.classes}</td>
                <td>${row.hours.toFixed(2)}</td>
                <td>${formatCurrency(row.monthlyFee)}</td>
                <td>${formatCurrency(row.monthlyCost)}</td>
                <td>${formatCurrency(row.monthlyFee - row.monthlyCost)}</td>
              </tr>`
          )
          .join("")}
      </tbody>
    </table>
  `;
  dom.monthlySummary.innerHTML = html;
}

function renderScheduleTable() {
  if (state.schedules.length === 0) {
    dom.scheduleTableWrap.innerHTML = "<p>尚未建立排課。</p>";
    return;
  }

  const html = `
    <table>
      <thead>
        <tr>
          <th>老師名稱</th>
          <th>學生名稱</th>
          <th>年級</th>
          <th>科目</th>
          <th>日期（可更改）</th>
          <th>星期</th>
          <th>上課</th>
          <th>下課</th>
          <th>時數</th>
          <th>學費時薪</th>
          <th>教師時薪</th>
          <th>每堂課費用</th>
          <th>課程型態</th>
          <th>成本</th>
          <th>刪除</th>
        </tr>
      </thead>
      <tbody>
        ${state.schedules
          .map(
            (row) => `
            <tr data-id="${row.id}">
              <td>${row.teacherName}</td>
              <td>${row.studentName}</td>
              <td>${row.grade}</td>
              <td>${row.subject}</td>
              <td><input type="date" value="${row.classDate}" data-action="change-date" /></td>
              <td>${row.weekday}</td>
              <td>${row.startTime}</td>
              <td>${row.endTime}</td>
              <td>${Number(row.classHours).toFixed(2)}</td>
              <td>${formatCurrency(row.tuitionHourlyRate)}</td>
              <td>${formatCurrency(row.teacherHourlySalary)}</td>
              <td>${formatCurrency(row.classFee)}</td>
              <td><span class="badge ${row.type === "補課" ? "makeup" : "normal"}">${row.type}</span></td>
              <td>${formatCurrency(row.classCost)}</td>
              <td><button type="button" class="remove-btn" data-action="remove-row">刪除</button></td>
            </tr>
          `
          )
          .join("")}
      </tbody>
    </table>
  `;
  dom.scheduleTableWrap.innerHTML = html;
}

function handleScheduleTableClick(event) {
  const actionTarget = event.target;
  if (!(actionTarget instanceof HTMLElement)) {
    return;
  }
  if (actionTarget.dataset.action !== "remove-row") {
    return;
  }
  const tr = actionTarget.closest("tr");
  if (!tr) {
    return;
  }
  const id = tr.dataset.id;
  state.schedules = state.schedules.filter((row) => row.id !== id);
  renderScheduleResult();
  saveState();
}

function handleScheduleTableInput(event) {
  const input = event.target;
  if (!(input instanceof HTMLInputElement)) {
    return;
  }
  if (input.dataset.action !== "change-date") {
    return;
  }
  const tr = input.closest("tr");
  if (!tr || !input.value) {
    return;
  }
  const id = tr.dataset.id;
  const row = state.schedules.find((item) => item.id === id);
  if (!row) {
    return;
  }
  row.classDate = input.value;
  row.weekday = getWeekdayText(input.value);
  state.schedules.sort((a, b) => (a.classDate > b.classDate ? 1 : -1));
  renderScheduleResult();
  saveState();
}

function exportSchedulesToExcel() {
  if (state.schedules.length === 0) {
    showToast("目前沒有可匯出的排課資料");
    return;
  }
  if (typeof XLSX === "undefined") {
    showToast("Excel 模組未載入，請稍後重試");
    return;
  }

  const scheduleRows = state.schedules.map((row) => ({
    老師名稱: row.teacherName,
    學生名稱: row.studentName,
    年級: row.grade,
    科目: row.subject,
    日期: row.classDate,
    星期: row.weekday,
    課程重複週期: row.recurrence === "weekly" ? "每週" : "每月",
    排課長度_月: row.durationMonths,
    上課時間: row.startTime,
    下課時間: row.endTime,
    總時數: Number(row.classHours).toFixed(2),
    學費時薪: row.tuitionHourlyRate,
    教師時薪_成本: row.teacherHourlySalary,
    每堂課費用: Number(row.classFee).toFixed(2),
    每堂課成本: Number(row.classCost).toFixed(2),
    課程型態: row.type
  }));

  const monthlyRows = buildMonthlySummary().map((row) => ({
    月份: row.month,
    堂數: row.classes,
    總時數: row.hours.toFixed(2),
    每月費用: row.monthlyFee.toFixed(2),
    每月成本: row.monthlyCost.toFixed(2),
    每月毛利: (row.monthlyFee - row.monthlyCost).toFixed(2)
  }));

  const totals = calculateSummary();
  const summaryRows = [
    { 指標: "排課堂數", 數值: totals.classes },
    { 指標: "總時數", 數值: totals.totalHours.toFixed(2) },
    { 指標: "每次收費總計", 數值: totals.totalFee.toFixed(2) },
    { 指標: "總成本", 數值: totals.totalCost.toFixed(2) },
    { 指標: "毛利", 數值: totals.grossProfit.toFixed(2) }
  ];

  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(scheduleRows), "排課明細");
  XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(monthlyRows), "月份費用");
  XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(summaryRows), "總覽");

  XLSX.writeFile(wb, `排課結果_${formatDate(new Date())}.xlsx`);
  showToast("已匯出 Excel");
}

function importMasterData() {
  const file = dom.masterImportFile.files?.[0];
  if (!file) {
    showToast("請先選擇 Excel 檔案");
    return;
  }
  if (typeof XLSX === "undefined") {
    showToast("Excel 模組尚未載入");
    return;
  }

  const reader = new FileReader();
  reader.onload = (e) => {
    try {
      const data = new Uint8Array(e.target.result);
      const wb = XLSX.read(data, { type: "array" });
      const nextMaster = {
        teachers: [],
        grades: [],
        subjects: [],
        hourlyRates: []
      };

      if (wb.Sheets.Teachers) {
        const rows = XLSX.utils.sheet_to_json(wb.Sheets.Teachers);
        nextMaster.teachers = rows
          .map((row) => ({
            name: String(row.name ?? row.老師名稱 ?? "").trim(),
            salary: Number(row.salary ?? row.教師時薪 ?? 0)
          }))
          .filter((item) => item.name);
      }
      if (wb.Sheets.Grades) {
        const rows = XLSX.utils.sheet_to_json(wb.Sheets.Grades);
        nextMaster.grades = rows
          .map((row) => String(row.name ?? row.年級 ?? "").trim())
          .filter(Boolean);
      }
      if (wb.Sheets.Subjects) {
        const rows = XLSX.utils.sheet_to_json(wb.Sheets.Subjects);
        nextMaster.subjects = rows
          .map((row) => String(row.name ?? row.科目 ?? "").trim())
          .filter(Boolean);
      }
      if (wb.Sheets.HourlyRates) {
        const rows = XLSX.utils.sheet_to_json(wb.Sheets.HourlyRates);
        nextMaster.hourlyRates = rows
          .map((row) => ({
            name: String(row.name ?? row.方案名稱 ?? "").trim(),
            value: Number(row.value ?? row.時薪 ?? 0)
          }))
          .filter((item) => item.name);
      }

      state.masterData = {
        teachers: nextMaster.teachers.length ? nextMaster.teachers : state.masterData.teachers,
        grades: nextMaster.grades.length ? nextMaster.grades : state.masterData.grades,
        subjects: nextMaster.subjects.length ? nextMaster.subjects : state.masterData.subjects,
        hourlyRates: nextMaster.hourlyRates.length ? nextMaster.hourlyRates : state.masterData.hourlyRates
      };
      renderAll();
      saveState();
      showToast("主檔匯入完成");
    } catch (error) {
      console.error(error);
      showToast("主檔匯入失敗，請檢查檔案格式");
    }
  };
  reader.readAsArrayBuffer(file);
}

function addMasterItem(type) {
  if (type === "teacher") {
    const name = dom.teacherNameInput.value.trim();
    const salary = Number(dom.teacherSalaryInput.value);
    if (!name || salary <= 0) {
      showToast("請輸入老師名稱與正確時薪");
      return;
    }
    state.masterData.teachers.push({ name, salary });
    dom.teacherNameInput.value = "";
    dom.teacherSalaryInput.value = "";
  } else if (type === "grade") {
    const grade = dom.gradeInput.value.trim();
    if (!grade) {
      showToast("請輸入年級");
      return;
    }
    state.masterData.grades.push(grade);
    dom.gradeInput.value = "";
  } else if (type === "subject") {
    const subject = dom.subjectInput.value.trim();
    if (!subject) {
      showToast("請輸入科目");
      return;
    }
    state.masterData.subjects.push(subject);
    dom.subjectInput.value = "";
  } else if (type === "rate") {
    const name = dom.rateNameInput.value.trim();
    const value = Number(dom.rateValueInput.value);
    if (!name || value <= 0) {
      showToast("請輸入方案名稱與正確時薪");
      return;
    }
    state.masterData.hourlyRates.push({ name, value });
    dom.rateNameInput.value = "";
    dom.rateValueInput.value = "";
  }

  renderAll();
  saveState();
}

function resetMasterData() {
  state.masterData = {
    teachers: [{ name: "王老師", salary: 550 }],
    grades: ["小六", "國一", "國二", "高一"],
    subjects: ["數學", "英文", "自然"],
    hourlyRates: [{ name: "一般班", value: 700 }, { name: "衝刺班", value: 850 }]
  };
  renderAll();
  saveState();
  showToast("主檔已重設");
}

function clearSchedules() {
  state.schedules = [];
  state.skipDates = [];
  state.makeupDates = [];
  renderAll();
  saveState();
  showToast("排課資料已清空");
}

let toastTimer;
function showToast(message) {
  dom.toast.textContent = message;
  dom.toast.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    dom.toast.classList.remove("show");
  }, 1700);
}

function bindEvents() {
  dom.firstClassDate.addEventListener("change", updateWeekdayDisplay);
  dom.startTime.addEventListener("change", updateClassHours);
  dom.endTime.addEventListener("change", updateClassHours);
  dom.hourlyRateTypeSelect.addEventListener("change", handleRateTypeChange);
  dom.teacherSelect.addEventListener("change", handleTeacherChange);
  dom.scheduleForm.addEventListener("submit", handleCreateSchedule);
  dom.addSkipDateBtn.addEventListener("click", () => addExceptionDate("skip"));
  dom.addMakeupDateBtn.addEventListener("click", () => addExceptionDate("makeup"));
  dom.scheduleTableWrap.addEventListener("click", handleScheduleTableClick);
  dom.scheduleTableWrap.addEventListener("input", handleScheduleTableInput);
  dom.exportExcelBtn.addEventListener("click", exportSchedulesToExcel);
  dom.importMasterBtn.addEventListener("click", importMasterData);
  dom.resetMasterBtn.addEventListener("click", resetMasterData);
  dom.clearSchedulesBtn.addEventListener("click", clearSchedules);
  dom.addTeacherBtn.addEventListener("click", () => addMasterItem("teacher"));
  dom.addGradeBtn.addEventListener("click", () => addMasterItem("grade"));
  dom.addSubjectBtn.addEventListener("click", () => addMasterItem("subject"));
  dom.addRateBtn.addEventListener("click", () => addMasterItem("rate"));
}

bindEvents();
loadState();
