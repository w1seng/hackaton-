const axios = require("axios");
const cheerio = require("cheerio");
const iconv = require("iconv-lite");
const fs = require("fs");

const BASE_URL = "https://dekanat.nung.edu.ua/cgi-bin/timetable.cgi";

function normalizeText(text) {
  return text.replace(/\s+/g, " ").trim();
}

function formatTime(text) {
  const match = text.match(/\d{2}:\d{2}/);
  return match ? match[0] : "";
}

function extractRoom(text) {
  const match = text.match(/(\d+[.\wА-Яа-яІіЇїЄєҐґA-Za-z]+)\.ауд\.?/i);
  return match ? match[1] : "";
}

function removeRoom(text) {
  return text
    .replace(/\s*\d+[.\wА-Яа-яІіЇїЄєҐґA-Za-z]*\.ауд\.?/gi, "")
    .trim();
}

function splitMultipleLessons(text) {
  const cleaned = normalizeText(text);

  const lessonStartRegex = /(?=[А-ЯІЇЄҐ][^.!?]*?\((Л|Лаб|Пр)\))/g;

  return cleaned
    .split(lessonStartRegex)
    .map(x => x.trim())
    .filter(x => x.length > 10 && /\((Л|Лаб|Пр)\)/.test(x));
}

function parseLesson(text) {
  text = normalizeText(text);

  const room = extractRoom(text);

  const teacherRegex =
    /(доцент|асистент|професор|ст\.?\s*викладач|викладач)\s+([А-ЯІЇЄҐ][а-яіїєґ']+\s+[А-ЯІЇЄҐ][а-яіїєґ']+\s+[А-ЯІЇЄҐ][а-яіїєґ']+)/i;

  const match = text.match(teacherRegex);

  if (!match) {
    return {
      subject: removeRoom(text),
      teacher: "",
      room
    };
  }

  const teacherFull = match[0];
  const teacherIndex = match.index;

  const subject = text.slice(0, teacherIndex).trim();

  return {
    subject: removeRoom(subject),
    teacher: removeRoom(teacherFull),
    room
  };
}

async function getSchedule(groupId = "-2030") {
  const response = await axios.get(`${BASE_URL}?n=700&group=${groupId}`, {
    responseType: "arraybuffer"
  });

  const html = iconv.decode(response.data, "win1251");
  const $ = cheerio.load(html);

  const result = {};

  $(".col-md-6.col-sm-6.col-xs-12.col-print-6").each((_, dayBlock) => {
    const date = normalizeText($(dayBlock).find("h4").first().text());

    if (!date) return;

    result[date] = [];

    $(dayBlock).find("table tr").each((_, row) => {
      const cols = $(row).find("td");

      if (cols.length < 3) return;

      const time = formatTime($(cols[1]).text());
      const fullText = normalizeText($(cols[2]).text());

      if (!time || !fullText) return;

      const lessons = splitMultipleLessons(fullText);
      const parsedLessons = lessons.length ? lessons : [fullText];

      parsedLessons.forEach(lessonText => {
        const parsed = parseLesson(lessonText);

        result[date].push({
          time,
          subject: parsed.subject,
          teacher: parsed.teacher,
          room: parsed.room
        });
      });
    });

    if (result[date].length === 0) {
      delete result[date];
    }
  });

  return result;
}

async function main() {
  const groupId = "-2030";

  const data = await getSchedule(groupId);

  fs.writeFileSync(
    "schedule.json",
    JSON.stringify(data, null, 2),
    "utf-8"
  );

  console.log("✅ schedule.json створено");
}

main().catch(console.error);