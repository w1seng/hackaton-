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
const CACHE_TIME = 10 * 60 * 1000; // 10 хв
let lastUpdate = {};

/* ================= HELPERS ================= */

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
  return text.replace(/\s*\d+[.\wА-Яа-яІіЇїЄєҐґA-Za-z]*\.ауд\.?/gi, "").trim();
}

function splitLessons(text) {
  const cleaned = normalizeText(text);
  const regex = /(?=[А-ЯІЇЄҐ].*?\((Л|Лаб|Пр)\))/g;

  return cleaned
    .split(regex)
    .map(x => x.trim())
    .filter(x => x.length > 8);
}

/* ================= PARSER ================= */

function parseLesson(text) {
  const room = extractRoom(text);

  return {
    subject: removeRoom(text),
    teacher: "",
    room
  };
}

/* ================= FETCH ================= */

async function fetchSchedule(groupId) {
  const response = await axios.get(
    `${BASE_URL}?n=700&group=${groupId}`,
    { responseType: "arraybuffer" }
  );

  const html = iconv.decode(response.data, "win1251");
  const $ = cheerio.load(html);

  const result = {};

  $(".col-md-6.col-sm-6.col-xs-12.col-print-6").each((_, day) => {
    const date = normalizeText($(day).find("h4").first().text());
    if (!date) return;

    result[date] = [];

    $(day).find("tr").each((_, row) => {
      const cols = $(row).find("td");
      if (cols.length < 3) return;

      const time = formatTime($(cols[1]).text());
      const text = normalizeText($(cols[2]).text());

      if (!time || !text) return;

      const lessons = splitLessons(text);

      lessons.forEach(l => {
        const parsed = parseLesson(l);

        result[date].push({
          time,
          subject: parsed.subject,
          teacher: parsed.teacher,
          room: parsed.room
        });
      });
    });

    if (result[date].length === 0) delete result[date];
  });

  return result;
}

/* ================= API ================= */

app.get("/api/schedule/:group", async (req, res) => {
  const group = req.params.group;

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
    console.log(err.message);
    res.status(500).json({ error: "schedule error" });
  }
});

/* ================= START ================= */

app.listen(3000, () => {
  console.log("Server running: http://localhost:3000");
});