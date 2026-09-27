/**
 * 만족도 조사 응답 수집용 Google Apps Script
 *
 * 설치 방법
 * 1) 새 Google 스프레드시트 → 확장 프로그램 → Apps Script
 * 2) 이 코드를 붙여넣고 저장
 * 3) 배포 → 새 배포 → 유형: 웹 앱
 *    - 실행 사용자: 나
 *    - 액세스 권한: 모든 사용자
 * 4) 발급된 웹 앱 URL(https://script.google.com/macros/s/.../exec)을
 *    index.html 의 CONFIG.ENDPOINT 에 붙여넣기
 *
 * 코드를 수정한 뒤에는 반드시 새 버전으로 다시 배포해야 반영됩니다.
 * (배포 → 배포 관리 → 편집 → 버전: 새 버전 → 배포, URL은 그대로 유지)
 */
const SHEET_NAME = "응답";   // 기록할 시트 탭 이름 (없으면 자동 생성)
const MAX_BYTES = 20000;     // 요청 크기 상한

function doPost(e) {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(10000)) return json_({ ok: false, error: "busy" });
  try {
    if (!e || !e.postData || !e.postData.contents) throw new Error("empty body");
    if (e.postData.contents.length > MAX_BYTES) throw new Error("payload too large");

    const data = JSON.parse(e.postData.contents);
    if (!data || typeof data !== "object" || Array.isArray(data)) throw new Error("invalid payload");

    // 제출시각을 맨 앞 열로
    const record = Object.assign({ "제출시각": new Date() }, data);

    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sheet = ss.getSheetByName(SHEET_NAME) || ss.insertSheet(SHEET_NAME);

    // 기존 머리글 + 새로 들어온 키를 열로 추가 (문항이 늘어나도 응답이 버려지지 않음)
    let headers = sheet.getLastRow() === 0
      ? []
      : sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
    const newKeys = Object.keys(record).filter(k => !headers.includes(k));
    if (newKeys.length) {
      sheet.getRange(1, headers.length + 1, 1, newKeys.length).setValues([newKeys]);
      headers = headers.concat(newKeys);
      sheet.setFrozenRows(1);
    }

    const row = headers.map(h =>
      Object.prototype.hasOwnProperty.call(record, h) ? clean_(record[h]) : ""
    );
    sheet.appendRow(row);
    return json_({ ok: true });
  } catch (err) {
    return json_({ ok: false, error: String((err && err.message) || err) });
  } finally {
    lock.releaseLock();
  }
}

// 브라우저로 URL을 열었을 때 동작 확인용
function doGet() {
  return json_({ ok: true, message: "survey endpoint alive" });
}

function clean_(v) {
  if (v === null || v === undefined) return "";
  if (v instanceof Date) return v;
  if (Array.isArray(v)) v = v.join(", ");
  else if (typeof v === "object") v = JSON.stringify(v);
  // 수식 주입 방지: =, +, -, @ 로 시작하는 문자열은 텍스트로 강제
  if (typeof v === "string" && /^[=+\-@]/.test(v)) return "'" + v;
  return v;
}

function json_(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
