(function (root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (typeof window !== "undefined") window.LessonFile = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  function filename(doc) {
    if (doc.filename) {
      return doc.filename.toLowerCase().endsWith(".docx") ? doc.filename : `${doc.filename}.docx`;
    }
    const header = doc.header || {};
    if (header.week && header.grade && header.lesson) {
      return `${header.week}-${header.grade}-${header.lesson}.docx`;
    }
    return "题目.docx";
  }

  function buildParagraphs(doc) {
    if (Array.isArray(doc.paragraphs)) return doc.paragraphs.slice();
    const header = doc.header || {};
    const lines = [
      `课次：${header.week || ""}`,
      `使用年级：${header.grade || ""}`,
      `课次：${header.lesson || ""}`,
    ];
    for (const section of doc.sections || sectionsFromParts(doc)) {
      lines.push("");
      lines.push(section.heading);
      for (const line of section.lines || []) lines.push(line);
    }
    return lines;
  }

  function sectionsFromParts(doc) {
    const header = doc.header || {};
    const sections = [];
    for (const item of doc.lessons || []) {
      sections.push({
        heading: `${item.star}星-${item.role}`,
        lines: item.lines || lessonLines(item),
      });
    }
    for (const item of doc.homework || []) {
      if (!hasQuestion(item)) continue;
      const star = item.star == null ? "" : `（${item.star}星）`;
      sections.push({
        heading: item.heading || `${item.level}-作业题${star}`,
        lines: item.lines || homeworkLines(item),
      });
    }
    for (const item of doc.promotion || []) {
      if (!hasQuestion(item)) continue;
      sections.push({
        heading: "晋级题",
        lines: item.lines || promotionLines(item, header),
      });
    }
    return sections;
  }

  function hasQuestion(item) {
    return Boolean(
      (item.lines && item.lines.length)
      || (item.body && item.body.length)
      || (item.steps && item.steps.length)
      || item.prompt
      || item.answer
      || item.analysis,
    );
  }

  function lessonLines(item) {
    const lines = [`题目：${item.prompt || ""}`];
    pushBody(lines, item);
    if (item.method) lines.push("解题方法");
    return lines;
  }

  function homeworkLines(item) {
    const lines = ["题目"];
    if (item.prompt) lines.push(item.prompt);
    lines.push("答案");
    if (item.answer) lines.push(item.answer);
    lines.push("解析");
    if (item.analysis) lines.push(item.analysis);
    for (const step of item.steps || []) lines.push(step);
    return lines;
  }

  function promotionLines(item, header) {
    const star = String(item.star == null ? "" : item.star);
    const token = star.endsWith("star") ? star : `${star}star`;
    const courseId = item.courseId || [header.week, header.grade, header.lesson, token].filter(Boolean).join("-");
    const lines = [
      `星级：${token}`,
      `课件 ID：${courseId}`,
      `题目类型：${item.type || ""}`,
      `题目：${item.prompt || ""}`,
      `答案：${item.answer || ""}`,
      `解析：${item.analysis || ""}`,
    ];
    for (const step of item.steps || []) lines.push(step);
    return lines;
  }

  function pushBody(lines, item) {
    for (const line of item.body || []) lines.push(line);
    lines.push(`答案：${item.answer || ""}`);
    lines.push(`解析：${item.analysis || ""}`);
    for (const step of item.steps || []) lines.push(step);
  }

  function buildDocx(doc) {
    const paragraphs = buildParagraphs(doc);
    const documentXml = [
      '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
      '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">',
      "<w:body>",
      ...paragraphs.map(paragraphXml),
      "<w:sectPr>",
      '<w:pgSz w:w="11906" w:h="16838"/>',
      '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/>',
      "</w:sectPr>",
      "</w:body>",
      "</w:document>",
    ].join("");
    return zipStore([
      { name: "[Content_Types].xml", data: textBytes(CONTENT_TYPES) },
      { name: "_rels/.rels", data: textBytes(PACKAGE_RELS) },
      { name: "word/document.xml", data: textBytes(documentXml) },
      { name: "word/styles.xml", data: textBytes(STYLES) },
      { name: "word/_rels/document.xml.rels", data: textBytes(DOCUMENT_RELS) },
    ]);
  }

  function paragraphXml(text) {
    if (!text) return "<w:p/>";
    return `<w:p><w:r><w:t xml:space="preserve">${escapeXml(text)}</w:t></w:r></w:p>`;
  }

  function escapeXml(text) {
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function textBytes(value) {
    return new TextEncoder().encode(value);
  }

  const CONTENT_TYPES = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>`;

  const PACKAGE_RELS = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>`;

  const DOCUMENT_RELS = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>`;

  const STYLES = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
    <w:qFormat/>
  </w:style>
</w:styles>`;

  function zipStore(files) {
    const locals = [];
    const centrals = [];
    let offset = 0;
    for (const file of files) {
      const name = textBytes(file.name);
      const crc = crc32(file.data);
      const local = new ByteWriter();
      local.u32(0x04034b50);
      local.u16(20);
      local.u16(0x0800);
      local.u16(0);
      local.u16(0);
      local.u16(0);
      local.u32(crc);
      local.u32(file.data.length);
      local.u32(file.data.length);
      local.u16(name.length);
      local.u16(0);
      local.bytes(name);
      local.bytes(file.data);
      const localBytes = local.toUint8Array();
      locals.push(localBytes);

      const central = new ByteWriter();
      central.u32(0x02014b50);
      central.u16(20);
      central.u16(20);
      central.u16(0x0800);
      central.u16(0);
      central.u16(0);
      central.u16(0);
      central.u32(crc);
      central.u32(file.data.length);
      central.u32(file.data.length);
      central.u16(name.length);
      central.u16(0);
      central.u16(0);
      central.u16(0);
      central.u16(0);
      central.u32(0);
      central.u32(offset);
      central.bytes(name);
      centrals.push(central.toUint8Array());
      offset += localBytes.length;
    }
    const centralBytes = concat(centrals);
    const end = new ByteWriter();
    end.u32(0x06054b50);
    end.u16(0);
    end.u16(0);
    end.u16(files.length);
    end.u16(files.length);
    end.u32(centralBytes.length);
    end.u32(offset);
    end.u16(0);
    return concat([...locals, centralBytes, end.toUint8Array()]);
  }

  class ByteWriter {
    constructor() {
      this.chunks = [];
      this.length = 0;
    }

    u16(value) {
      const bytes = new Uint8Array(2);
      new DataView(bytes.buffer).setUint16(0, value, true);
      this.bytes(bytes);
    }

    u32(value) {
      const bytes = new Uint8Array(4);
      new DataView(bytes.buffer).setUint32(0, value, true);
      this.bytes(bytes);
    }

    bytes(value) {
      this.chunks.push(value);
      this.length += value.length;
    }

    toUint8Array() {
      return concat(this.chunks);
    }
  }

  function concat(parts) {
    const out = new Uint8Array(parts.reduce((sum, part) => sum + part.length, 0));
    let offset = 0;
    for (const part of parts) {
      out.set(part, offset);
      offset += part.length;
    }
    return out;
  }

  const CRC_TABLE = (() => {
    const table = new Uint32Array(256);
    for (let n = 0; n < 256; n += 1) {
      let c = n;
      for (let k = 0; k < 8; k += 1) c = (c & 1) ? (0xedb88320 ^ (c >>> 1)) : (c >>> 1);
      table[n] = c >>> 0;
    }
    return table;
  })();

  function crc32(data) {
    let c = 0xffffffff;
    for (let i = 0; i < data.length; i += 1) c = CRC_TABLE[(c ^ data[i]) & 0xff] ^ (c >>> 8);
    return (c ^ 0xffffffff) >>> 0;
  }

  return { filename, buildParagraphs, buildDocx };
});
