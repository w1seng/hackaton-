const express = require("express");
const axios = require("axios");
const cheerio = require("cheerio");
const iconv = require("iconv-lite");
const cors = require("cors");

const app = express();

app.use(cors());
app.use(express.static(__dirname));

const BASE_URL = "https://dekanat.nung.edu.ua/cgi-bin/timetable.cgi";

const GROUP_IDS = {
  "ІВЕ-22-1": "-1624",
  "ІВЕ-23-1": "-1885",
  "ІВЕ-24-1": "-2061",
  "ІВЕ-25-1": "-2358",
  "ІП-22-1": "-1614",
  "ІП-22-2": "-1615",
  "ІП-22-3": "-1616",
  "ІП-22-4": "-1617",
  "ІП-23-1": "-1886",
  "ІП-23-2": "-1887",
  "ІП-23-3": "-1888",
  "ІП-23-4": "-1889",
  "ІП-24-1": "-2030",
  "ІП-24-1К": "-1981",
  "ІП-24-2": "-2038",
  "ІП-24-3": "-2039",
  "ІП-25-1": "-2277",
  "ІП-25-2": "-2278",
  "ІП-25-3": "-2387",
  "ІП-25-4К": "-2279",
  "ІПМ-25-1": "-2224",
  "ІПМ-25-2": "-2227",
  "ІС-22-1": "-1481",
  "ІС-23-1": "-1773",
  "ІС-24-1": "-2046",
  "ІС-25-1": "-2296",
  "ІСТ-22-1": "-1541",
  "ІСТ-23-1": "-1896",
  "ІСТ-24-1": "-2059",
  "ІСТ-25-1": "-2275",
  "ІСМ-25-1": "-2297",
  "ІТЕМ-25-1": "-2219",
  "А-C1-25": "-2236",
  "А-D3-25": "-2235",
  "А-D4-25": "-2234",
  "А-E2-25": "-2232",
  "А-E4-25": "-2231",
  "А-F7-25": "-2230",
  "А-G11-25": "-2208",
  "А-G16-25": "-2207",
  "А-G2-25": "-2228",
  "А-G6-25": "-2217",
  "А-G7-25": "-2216",
  "А-G9-25": "-2215",
  "А051-24": "-2014",
  "А073-24": "-2018",
  "А076-24": "-2020",
  "А101-24": "-2021",
  "А103-24": "-2025",
  "А123-24": "-2175",
  "А131-24": "-2033",
  "А133-24": "-2036",
  "А174-24": "-2037",
  "А175-24": "-2073",
  "А183-24": "-2074",
  "А185-24": "-2075",
  "АКП-23-1": "-1916",
  "АКП-24-1": "-2006",
  "АКП-24-1К": "-1980",
  "АКП-24-2К": "-2169",
  "АКП-25-1": "-2314",
  "АКП-25-2": "-2379",
  "АКП-25-3К": "-2315",
  "АКПМ-25-1": "-2312",
  "АКСМ-25-1": "-2218",
  "АМ-22-1": "-1655",
  "АМ-23-1": "-1770",
  "АМ-23-2": "-1944",
  "АМ-24-1": "-2091",
  "АМ-24-2": "-2092",
  "АМ-25-1": "-2222",
  "АМ-25-2": "-2223",
  "АММ-25-1": "-2301",
  "АТ-22-1": "-1664",
  "АТ-22-2": "-1665",
  "АТ-23-1": "-1835",
  "АТ-23-2": "-1952",
  "АТ-23-3": "-2161",
  "АТ-24-1": "-2083",
  "АТ-24-2": "-2084",
  "АТ-25-1": "-2195",
  "АТ-25-2": "-2196",
  "АТМ-25-1": "-2192",
  "Б-22-1": "-1660",
  "Б-22-2": "-1661",
  "Б-22-3": "-1735",
  "Б-23-1": "-1803",
  "Б-23-2": "-1805",
  "Б-23-3": "-1806",
  "Б-24-1": "-2093",
  "Б-24-2": "-2094",
  "Б-24-3": "-2095",
  "Б-25-1": "-2225",
  "Б-25-2": "-2226",
  "Б-25-3": "-2251",
  "Б-25-4": "-2390",
  "БМ-25-1": "-2302",
  "ВК-22-1": "-1647",
  "ВК-23-1": "-1872",
  "ВК-24-1": "-2156",
  "ВК-25-1": "-2290",
  "ГЗ-22-1": "-1591",
  "ГЗ-23-1": "-1873",
  "ГЗ-24-1": "-2096",
  "ГЗ-24-1К": "-2041",
  "ГЗ-25-1": "-2256",
  "ГЗ-25-2": "-2384",
  "ГЗГМ-25-1": "-2306",
  "ГЗЗМ-25-1": "-2307",
  "ГМІ-22-1": "-1552",
  "ГМІ-23-1": "-1829",
  "ГМІ-24-1": "-2048",
  "ГМІ-25-1": "-2240",
  "ГМП-23-1": "-1831",
  "ГМП-24-1": "-2049",
  "ГМП-25-1": "-2229",
  "ГР-22-1": "-1566",
  "ГР-22-2": "-1642",
  "ГФ-23-1": "-1738",
  "ГФ-24-1": "-2109",
  "ГФ-24-2": "-2160",
  "ГФ-25-1": "-2300",
  "ГФ-25-2": "-2376",
  "ГФМ-25-1": "-2299",
  "ЕК-22-1": "-1507",
  "ЕК-23-1": "-1755",
  "ЕК-24-1": "-2026",
  "ЕК-25-1": "-2337",
  "ЕКО-22-1": "-1611",
  "ЕКО-23-1": "-1778",
  "ЕКО-24-1": "-2055",
  "ЕКО-25-1": "-2199",
  "ЕКОМ-25-1": "-2291",
  "ЕКМ-25-1": "-2329",
  "ЕМВМ-25-1": "-2357",
  "ЕТ-22-1": "-1486",
  "ЕТ-22-2": "-1487",
  "ЕТ-22-3": "-1494",
  "ЕТ-23-1": "-1742",
  "ЕТ-23-2": "-1743",
  "ЕТ-23-3": "-1744",
  "ЕТ-23-4": "-1950",
  "ЕТ-24-1": "-2087",
  "ЕТ-24-2": "-2088",
  "ЕТ-24-3": "-2089",
  "ЕТ-24-4": "-2090",
  "ЕТ-25-1": "-2318",
  "ЕТ-25-2": "-2319",
  "ЕТ-25-3": "-2320",
  "ЕТ-25-4К": "-2378",
  "ЕТММ-25-1": "-2317",
  "ЕТСМ-25-1": "-2316",
  "ЗТ-22-1": "-1550",
  "ЗТ-23-1": "-1823",
  "ЗТ-23-1К": "-1824",
  "ЗТ-24-1": "-2086",
  "ЗТ-25-1": "-2200",
  "КІ-22-1": "-1618",
  "КІ-22-2": "-1619",
  "КІ-23-1": "-1898",
  "КІ-23-2": "-1899",
  "КІ-24-1": "-2053",
  "КІ-25-1": "-2281"
};

const cache = {};
const CACHE_TIME = 10 * 60 * 1000;
const lastUpdate = {};

function normalizeText(text) {
  return String(text || "").replace(/\s+/g, " ").trim();
}

function normalizeGroup(text) {
  return String(text || "")
    .toUpperCase()
    .replace(/\s+/g, "")
    .trim();
}

function resolveGroupId(groupName) {
  const key = normalizeGroup(groupName);
  return GROUP_IDS[key] || groupName;
}

function formatTime(text) {
  const match = String(text || "").match(/\d{2}:\d{2}/);
  return match ? match[0] : "";
}

function extractRoom(text) {
  const match = String(text || "").match(/(\d+[.\wА-Яа-яІіЇїЄєҐґA-Za-z]+)\.ауд\.?/i);
  return match ? match[1] : "";
}

function removeRoom(text) {
  return String(text || "")
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

  return {
    subject: removeRoom(text.slice(0, match.index)),
    teacher: removeRoom(match[0]),
    room
  };
}

async function fetchSchedule(groupId) {
  const response = await axios.get(
    `${BASE_URL}?n=700&group=${encodeURIComponent(groupId)}`,
    {
      responseType: "arraybuffer"
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

app.get("/api/schedule/:group", async (req, res) => {
  const groupName = decodeURIComponent(req.params.group).trim();
  const groupId = resolveGroupId(groupName);

  try {
    const now = Date.now();

    if (
      cache[groupId] &&
      lastUpdate[groupId] &&
      now - lastUpdate[groupId] < CACHE_TIME
    ) {
      return res.json(cache[groupId]);
    }

    const data = await fetchSchedule(groupId);

    cache[groupId] = data;
    lastUpdate[groupId] = now;

    res.json(data);
  } catch (err) {
    console.error("Schedule error:", err.message);
    res.status(500).json({
      error: "schedule error"
    });
  }
});

app.listen(3000, () => {
  console.log("🚀 Server running: http://localhost:3000");
});