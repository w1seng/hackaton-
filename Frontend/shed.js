const express = require("express");
const axios = require("axios");
const cheerio = require("cheerio");
const iconv = require("iconv-lite");
const cors = require("cors");

const app = express();

app.use(cors());
app.use(express.static(__dirname));

const BASE_URL = "https://dekanat.nung.edu.ua/cgi-bin/timetable.cgi";

/* ================= CACHE ================= */

const cache = {};
const CACHE_TIME = 10 * 60 * 1000;
const lastUpdate = {};

/* ================= HELPERS ================= */

function normalizeText(text) {
  return String(text || "").replace(/\s+/g, " ").trim();
}

function formatTime(text) {
  const match = String(text || "").match(/\d{2}:\d{2}/);
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

function splitLessons(text) {
  const cleaned = normalizeText(text);

  const parts = cleaned
    .split(/(?=[А-ЯІЇЄҐ][^.!?]*?\((Л|Лаб|Пр)\))/g)
    .map(x => x.trim())
    .filter(x => x.length > 8 && /\((Л|Лаб|Пр)\)/.test(x));

  return parts.length ? parts : [cleaned];
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

  const teacher = removeRoom(match[0]);
  const subject = removeRoom(text.slice(0, match.index));

  return {
    subject,
    teacher,
    room
  };
}

/* ================= FETCH SCHEDULE ================= */

async function fetchSchedule(groupName) {
  const params = new URLSearchParams();

  params.append("faculty", "0");
  params.append("teacher", "");
  params.append("course", "0");
  params.append("group", groupName);
  params.append("sdate", "");
  params.append("edate", "");
  params.append("n", "700");

  const response = await axios.post(
    `${BASE_URL}?n=700`,
    params.toString(),
    {
      responseType: "arraybuffer",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded"
      }
    }
  );

  const html = iconv.decode(response.data, "win1251");
  const $ = cheerio.load(html);

  const result = {};

  $(".col-md-6.col-sm-6.col-xs-12.col-print-6").each((_, day) => {
    const date = normalizeText($(day).find("h4").first().text());

    if (!date) return;

    result[date] = [];

    $(day).find("table tr").each((_, row) => {
      const cols = $(row).find("td");

      if (cols.length < 3) return;

      const time = formatTime($(cols[1]).text());
      const fullText = normalizeText($(cols[2]).text());

      if (!time || !fullText) return;

      const lessons = splitLessons(fullText);

      lessons.forEach(lessonText => {
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

/* ================= API ================= */

app.get("/api/schedule/:group", async (req, res) => {
  const group = decodeURIComponent(req.params.group).trim();

  try {
    const now = Date.now();

    if (
      cache[group] &&
      lastUpdate[group] &&
      now - lastUpdate[group] < CACHE_TIME
    ) {
      return res.json(cache[group]);
    }

    const data = await fetchSchedule(group);

    cache[group] = data;
    lastUpdate[group] = now;

    res.json(data);
  } catch (err) {
    console.error("Schedule error:", err.message);
    res.status(500).json({
      error: "schedule error"
    });
  }
});

/* ================= START ================= */

app.listen(3000, () => {
  console.log("Server running: http://localhost:3000");
});