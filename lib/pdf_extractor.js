/**
 * Dependency-free PDF text extractor.
 * Handles Flate-compressed content and object streams, page-tree ordering,
 * form XObjects, ToUnicode CMaps (Type0/CID fonts), and simple-font Differences.
 * It does not OCR scanned pages or decrypt protected files.
 */

const zlib = require("zlib");

const MAX_STREAM_BYTES = 32 * 1024 * 1024;
const MAX_PAGES = 5000;
const MAX_TEXT_CHARS = 5 * 1024 * 1024;
const DELIMS = "()<>[]{}/%";
const NUMBER = /^[+-]?(\d+\.?\d*|\.\d+)$/;

const isWhitespace = c => c === " " || c === "\n" || c === "\r" || c === "\t" || c === "\f" || c === "\0";
const isDict = v => v !== null && typeof v === "object" && !Array.isArray(v) && !Buffer.isBuffer(v) && v.ref === undefined;

const GLYPH_NAMES = {
    space: " ", period: ".", comma: ",", hyphen: "-", minus: "−", colon: ":", semicolon: ";", exclam: "!",
    question: "?", quotesingle: "'", quoteright: "’", quoteleft: "‘", quotedblleft: "“",
    quotedblright: "”", quotedbl: '"', endash: "–", emdash: "—", fi: "fi", fl: "fl", ff: "ff",
    ffi: "ffi", ffl: "ffl", parenleft: "(", parenright: ")", bracketleft: "[", bracketright: "]", slash: "/",
    ampersand: "&", percent: "%", dollar: "$", numbersign: "#", at: "@", asterisk: "*", plus: "+", equal: "=",
    less: "<", greater: ">", underscore: "_", bullet: "•", zero: "0", one: "1", two: "2", three: "3",
    four: "4", five: "5", six: "6", seven: "7", eight: "8", nine: "9",
};

function glyphToUnicode(name) {
    const glyph = name.slice(1);
    if (GLYPH_NAMES[glyph] !== undefined) return GLYPH_NAMES[glyph];
    if (/^[A-Za-z]$/.test(glyph)) return glyph;
    const uni = /^uni([0-9A-Fa-f]{4})$/.exec(glyph);
    return uni ? String.fromCharCode(parseInt(uni[1], 16)) : "";
}

class Lexer {
    constructor(text, pos = 0) {
        this.s = text;
        this.i = pos;
    }

    next() {
        const s = this.s, n = s.length;
        let i = this.i;
        for (;;) {
            while (i < n && isWhitespace(s[i])) i++;
            if (s[i] !== "%") break;
            while (i < n && s[i] !== "\n" && s[i] !== "\r") i++;
        }
        if (i >= n) { this.i = n; return null; }
        const c = s[i];
        if (c === "/") {
            let j = i + 1;
            while (j < n && !isWhitespace(s[j]) && !DELIMS.includes(s[j])) j++;
            this.i = j;
            const name = s.slice(i + 1, j).replace(/#([0-9a-fA-F]{2})/g, (_, h) => String.fromCharCode(parseInt(h, 16)));
            return { type: "name", v: "/" + name };
        }
        if (c === "(") return this.literalString(i);
        if (c === "<") {
            if (s[i + 1] === "<") { this.i = i + 2; return { type: "<<" }; }
            const end = s.indexOf(">", i);
            const stop = end < 0 ? n : end;
            let hex = s.slice(i + 1, stop).replace(/[^0-9a-fA-F]/g, "");
            if (hex.length % 2) hex += "0";
            this.i = stop + 1;
            return { type: "str", v: Buffer.from(hex, "hex") };
        }
        if (c === ">" && s[i + 1] === ">") { this.i = i + 2; return { type: ">>" }; }
        if (c === ">" || c === ")") { this.i = i + 1; return this.next(); }
        if (c === "[" || c === "]" || c === "{" || c === "}") { this.i = i + 1; return { type: c }; }
        let j = i;
        while (j < n && !isWhitespace(s[j]) && !DELIMS.includes(s[j])) j++;
        this.i = j;
        const word = s.slice(i, j);
        return NUMBER.test(word) ? { type: "num", v: parseFloat(word) } : { type: "kw", v: word };
    }

    literalString(start) {
        const s = this.s, n = s.length, bytes = [];
        const escapes = { n: 10, r: 13, t: 9, b: 8, f: 12 };
        let j = start + 1, depth = 1;
        while (j < n && depth > 0) {
            const ch = s[j++];
            if (ch === "\\") {
                const e = s[j++];
                if (e === undefined) break;
                if (escapes[e] !== undefined) bytes.push(escapes[e]);
                else if (e === "\r") { if (s[j] === "\n") j++; }
                else if (e === "\n") continue;
                else if (e >= "0" && e <= "7") {
                    let octal = e;
                    for (let k = 0; k < 2 && s[j] >= "0" && s[j] <= "7"; k++) octal += s[j++];
                    bytes.push(parseInt(octal, 8) & 255);
                } else bytes.push(e.charCodeAt(0) & 255);
            } else if (ch === "(") { depth++; bytes.push(40); }
            else if (ch === ")") { depth--; if (depth > 0) bytes.push(41); }
            else bytes.push(ch.charCodeAt(0) & 255);
        }
        this.i = j;
        return { type: "str", v: Buffer.from(bytes) };
    }
}

/** Parses one PDF value. Names are "/Name" strings, strings are Buffers, references are {ref}. */
function parseValue(lex, tok, depth = 0) {
    if (!tok || depth > 40) return null;
    switch (tok.type) {
        case "num": {
            if (Number.isInteger(tok.v) && tok.v >= 0) {
                const save = lex.i;
                const second = lex.next();
                if (second && second.type === "num" && Number.isInteger(second.v)) {
                    const third = lex.next();
                    if (third && third.type === "kw" && third.v === "R") return { ref: tok.v };
                }
                lex.i = save;
            }
            return tok.v;
        }
        case "name":
        case "str":
            return tok.v;
        case "kw":
            return tok.v === "true" ? true : tok.v === "false" ? false : null;
        case "[": {
            const items = [];
            for (let t = lex.next(); t && t.type !== "]"; t = lex.next()) items.push(parseValue(lex, t, depth + 1));
            return items;
        }
        case "<<": {
            const dict = Object.create(null);
            for (let k = lex.next(); k && k.type !== ">>"; k = lex.next()) {
                if (k.type !== "name") continue;
                const v = lex.next();
                if (!v || v.type === ">>") break;
                dict[k.v.slice(1)] = parseValue(lex, v, depth + 1);
            }
            return dict;
        }
        default:
            return null;
    }
}

function inflate(buffer) {
    try {
        return zlib.inflateSync(buffer, { maxOutputLength: MAX_STREAM_BYTES, finishFlush: zlib.constants.Z_SYNC_FLUSH });
    } catch {
        return null;
    }
}

function utf16Hex(hex) {
    if (hex.length <= 2) return String.fromCharCode(parseInt(hex || "0", 16));
    let out = "";
    for (let i = 0; i + 4 <= hex.length; i += 4) out += String.fromCharCode(parseInt(hex.slice(i, i + 4), 16));
    return out;
}

/** Parses a ToUnicode CMap into { map, codeLen }. */
function parseCMap(text) {
    const map = new Map();
    const space = /begincodespacerange\s*<([0-9a-fA-F]+)>/.exec(text);
    const codeLen = space ? Math.max(1, space[1].length / 2) : 0;
    for (const block of text.matchAll(/beginbfchar([\s\S]*?)endbfchar/g)) {
        for (const m of block[1].matchAll(/<([0-9a-fA-F]+)>\s*<([0-9a-fA-F]*)>/g)) map.set(parseInt(m[1], 16), utf16Hex(m[2]));
    }
    for (const block of text.matchAll(/beginbfrange([\s\S]*?)endbfrange/g)) {
        for (const m of block[1].matchAll(/<([0-9a-fA-F]+)>\s*<([0-9a-fA-F]+)>\s*(\[[^\]]*\]|<[0-9a-fA-F]*>)/g)) {
            const lo = parseInt(m[1], 16), hi = Math.min(parseInt(m[2], 16), lo + 65535);
            if (m[3][0] === "[") {
                const targets = [...m[3].matchAll(/<([0-9a-fA-F]*)>/g)];
                for (let code = lo; code <= hi && code - lo < targets.length; code++) map.set(code, utf16Hex(targets[code - lo][1]));
            } else {
                const base = utf16Hex(m[3].slice(1, -1));
                if (!base) continue;
                const head = base.slice(0, -1), last = base.charCodeAt(base.length - 1);
                for (let code = lo; code <= hi; code++) map.set(code, head + String.fromCharCode(last + code - lo));
            }
        }
    }
    return { map, codeLen };
}

/**
 * Extracts plain text from a PDF buffer.
 * @param {Buffer} buffer
 * @returns {string}
 */
function extractPdfText(buffer) {
    if (!buffer.subarray(0, 1024).toString("latin1").includes("%PDF-")) throw new Error("not a PDF file");
    const src = buffer.toString("latin1");
    if (/\/Encrypt\s*(?:<<|\d+\s+\d+\s+R)/.test(src)) throw new Error("the PDF is encrypted or password-protected");

    // ---- Pass 1: index every "N G obj" body (later definitions win, as with incremental updates).
    const objects = new Map();
    const objectPattern = /(\d+)\s+(\d+)\s+obj\b/g;
    let nextStream = -2;
    for (let m; (m = objectPattern.exec(src));) {
        const start = objectPattern.lastIndex;
        let endObj = src.indexOf("endobj", start);
        if (endObj < 0) endObj = src.length;
        if (nextStream !== -1 && nextStream < start) nextStream = src.indexOf("stream", start);
        const obj = { text: src, start, stream: null };
        if (nextStream !== -1 && nextStream < endObj) {
            let dataStart = nextStream + 6;
            if (src[dataStart] === "\r") dataStart++;
            if (src[dataStart] === "\n") dataStart++;
            const declared = /\/Length\s+(\d+)(?!\s+\d+\s+R)/.exec(src.slice(start, nextStream));
            let dataEnd = -1;
            if (declared) {
                const candidate = dataStart + parseInt(declared[1], 10);
                if (/^\s*endstream/.test(src.slice(candidate, candidate + 12))) dataEnd = candidate;
            }
            if (dataEnd < 0) {
                dataEnd = src.indexOf("endstream", dataStart);
                if (dataEnd < 0) dataEnd = endObj;
                if (src[dataEnd - 1] === "\n") dataEnd--;
                if (src[dataEnd - 1] === "\r") dataEnd--;
            }
            obj.stream = buffer.subarray(dataStart, dataEnd);
            obj.dictEnd = nextStream;
            objectPattern.lastIndex = dataEnd;
        }
        objects.set(parseInt(m[1], 10), obj);
    }

    const valueOf = obj => {
        if (!obj) return null;
        if (!("value" in obj)) {
            const lex = new Lexer(obj.text, obj.start);
            obj.value = parseValue(lex, lex.next());
        }
        return obj.value;
    };
    const resolve = (v, hops = 0) => {
        while (v && v.ref !== undefined && hops++ < 20) v = valueOf(objects.get(v.ref));
        return v;
    };
    const streamData = obj => {
        if (!obj || !obj.stream) return null;
        const dict = valueOf(obj);
        if (!isDict(dict)) return null;
        let filters = resolve(dict.Filter);
        filters = filters == null ? [] : (Array.isArray(filters) ? filters : [filters]).map(f => resolve(f));
        let data = obj.stream;
        for (const filter of filters) {
            if (filter !== "/FlateDecode" && filter !== "/Fl") return null;
            data = inflate(data);
            if (!data) return null;
        }
        return data;
    };

    // ---- Pass 2: expand object streams (PDF 1.5+).
    for (const obj of [...objects.values()]) {
        if (!obj.stream || !src.slice(obj.start, obj.dictEnd).includes("/ObjStm")) continue;
        const dict = valueOf(obj);
        const data = streamData(obj);
        if (!data || !isDict(dict)) continue;
        const text = data.toString("latin1");
        const header = text.slice(0, dict.First).trim().split(/\s+/).map(Number);
        for (let k = 0; k + 1 < header.length && k / 2 < (dict.N || 0); k += 2) {
            if (!objects.has(header[k])) objects.set(header[k], { text, start: dict.First + header[k + 1], stream: null });
        }
    }

    // ---- Page order from the page tree (falls back to scanning for /Type /Page).
    let root = null;
    const looseObjects = [];
    for (const [num, obj] of objects) {
        if (obj.stream) continue;
        const value = valueOf(obj);
        if (!isDict(value)) continue;
        if (value.Type === "/Catalog") root = value;
        else if (value.Type === "/Page") looseObjects.push({ page: value, resources: value.Resources, num });
    }
    const pages = [];
    const seen = new Set();
    const walk = (node, inherited) => {
        if (pages.length >= MAX_PAGES) return;
        if (node && node.ref !== undefined) {
            if (seen.has(node.ref)) return;
            seen.add(node.ref);
        }
        const dict = resolve(node);
        if (!isDict(dict)) return;
        const resources = dict.Resources !== undefined ? dict.Resources : inherited;
        const kids = resolve(dict.Kids);
        if (Array.isArray(kids)) kids.forEach(kid => walk(kid, resources));
        else pages.push({ page: dict, resources });
    };
    const rootPages = root && resolve(root.Pages);
    if (rootPages) walk(root.Pages, undefined);
    if (pages.length === 0) pages.push(...looseObjects);

    // ---- Fonts.
    const fontCache = new Map();
    const defaultFont = { simple: true, differences: null, width: () => 500 };
    const simpleWidths = dict => {
        const first = resolve(dict.FirstChar) || 0;
        const list = resolve(dict.Widths);
        const missing = isDict(resolve(dict.FontDescriptor)) ? resolve(resolve(dict.FontDescriptor).MissingWidth) : 0;
        return code => {
            const w = Array.isArray(list) ? resolve(list[code - first]) : undefined;
            return typeof w === "number" ? w : (missing || 500);
        };
    };
    const cidWidths = dict => {
        const descendant = resolve(resolve(dict.DescendantFonts) && resolve(dict.DescendantFonts)[0]);
        if (!isDict(descendant)) return () => 1000;
        const fallback = typeof resolve(descendant.DW) === "number" ? resolve(descendant.DW) : 1000;
        const table = new Map();
        const list = resolve(descendant.W);
        if (Array.isArray(list)) {
            for (let i = 0; i < list.length;) {
                const first = resolve(list[i]);
                const next = resolve(list[i + 1]);
                if (typeof first !== "number") { i++; continue; }
                if (Array.isArray(next)) {
                    next.forEach((w, k) => table.set(first + k, resolve(w)));
                    i += 2;
                } else {
                    const width = resolve(list[i + 2]);
                    if (typeof next !== "number") { i += 3; continue; }
                    for (let c = first; c <= Math.min(next, first + 65535); c++) table.set(c, width);
                    i += 3;
                }
            }
        }
        return code => (typeof table.get(code) === "number" ? table.get(code) : fallback);
    };
    const loadFont = ref => {
        if (ref && ref.ref !== undefined && fontCache.has(ref.ref)) return fontCache.get(ref.ref);
        const dict = resolve(ref);
        let font = defaultFont;
        if (isDict(dict)) {
            font = { type0: dict.Subtype === "/Type0", cmap: null, codeLen: 0, differences: null };
            font.width = font.type0 ? cidWidths(dict) : simpleWidths(dict);
            const cmapRef = dict.ToUnicode;
            const cmapObj = cmapRef && cmapRef.ref !== undefined ? objects.get(cmapRef.ref) : null;
            const cmapData = streamData(cmapObj);
            if (cmapData) {
                const parsed = parseCMap(cmapData.toString("latin1"));
                font.cmap = parsed.map;
                font.codeLen = parsed.codeLen || (font.type0 ? 2 : 1);
            } else if (font.type0) font.codeLen = 2;
            const encoding = resolve(dict.Encoding);
            if (isDict(encoding) && Array.isArray(resolve(encoding.Differences))) {
                font.differences = new Map();
                let code = 0;
                for (const item of resolve(encoding.Differences)) {
                    if (typeof item === "number") code = item;
                    else if (typeof item === "string") font.differences.set(code++, glyphToUnicode(item));
                }
            }
        }
        if (ref && ref.ref !== undefined) fontCache.set(ref.ref, font);
        return font;
    };
    const decode = (font, bytes) => {
        let out = "";
        if (font.cmap) {
            const step = font.codeLen === 2 ? 2 : 1;
            for (let i = 0; i + step <= bytes.length; i += step) {
                const code = step === 2 ? (bytes[i] << 8) | bytes[i + 1] : bytes[i];
                out += font.cmap.get(code) || "";
            }
        } else if (!font.type0) {
            for (const b of bytes) {
                const mapped = font.differences && font.differences.get(b);
                if (mapped !== undefined && mapped !== null) out += mapped;
                else if (b >= 32) out += String.fromCharCode(b);
            }
        }
        return out;
    };

    /** Total advance of a shown string in 1/1000 text-space units. */
    const advance = (font, bytes) => {
        const step = font.type0 ? 2 : 1;
        let total = 0;
        for (let i = 0; i + step <= bytes.length; i += step) {
            total += font.width(step === 2 ? (bytes[i] << 8) | bytes[i + 1] : bytes[i]);
        }
        return total;
    };

    // ---- Content stream interpreter.
    const extractPage = ({ page, resources }) => {
        const state = { font: defaultFont, size: 1, scale: 1, x: 0, lineX: 0, y: 0, lastY: null, moved: false, leading: 1, out: "" };
        const visited = new Set();
        const separate = () => {
            if (state.lastY !== null && state.out) {
                if (Math.abs(state.y - state.lastY) > 0.5) { if (!state.out.endsWith("\n")) state.out += "\n"; }
                else if (!/\s$/.test(state.out) && state.lineX - state.x > 0.15 * state.size * state.scale) state.out += " ";
            }
        };
        const show = bytes => {
            const text = decode(state.font, bytes);
            if (!text) return;
            if (state.moved) { separate(); state.moved = false; state.x = state.lineX; }
            state.lastY = state.y;
            state.out += text;
            state.x += advance(state.font, bytes) / 1000 * state.size * state.scale;
        };
        const run = (data, res, depth) => {
            const lex = new Lexer(data);
            const resDict = resolve(res);
            let stack = [];
            for (let tok = lex.next(); tok; tok = lex.next()) {
                if (state.out.length > MAX_TEXT_CHARS) return;
                if (tok.type === "num" || tok.type === "name" || tok.type === "str") { stack.push(tok.v); continue; }
                if (tok.type === "[" || tok.type === "<<") { stack.push(parseValue(lex, tok)); continue; }
                if (tok.type !== "kw") continue;
                switch (tok.v) {
                    case "true": case "false": case "null": stack.push(null); continue;
                    case "BT": state.y = 0; state.lineX = state.x = 0; state.scale = 1; state.moved = true; break;
                    case "Tf": {
                        const fonts = isDict(resDict) ? resolve(resDict.Font) : null;
                        const name = stack[0];
                        state.font = isDict(fonts) && typeof name === "string" && fonts[name.slice(1)] !== undefined
                            ? loadFont(fonts[name.slice(1)]) : defaultFont;
                        if (typeof stack[1] === "number") state.size = Math.abs(stack[1]) || 1;
                        break;
                    }
                    case "Tj": if (Buffer.isBuffer(stack[0])) show(stack[0]); break;
                    case "TJ":
                        if (Array.isArray(stack[0])) {
                            for (const part of stack[0]) {
                                if (Buffer.isBuffer(part)) show(part);
                                else if (typeof part === "number") {
                                    state.x -= part / 1000 * state.size * state.scale;
                                    if (part < -200 && state.out && !/\s$/.test(state.out)) state.out += " ";
                                }
                            }
                        }
                        break;
                    case "'": case '"': {
                        state.y -= state.leading; state.moved = true;
                        const text = stack[stack.length - 1];
                        if (Buffer.isBuffer(text)) show(text);
                        break;
                    }
                    case "TL": if (typeof stack[0] === "number") state.leading = stack[0] || 1; break;
                    case "Td": case "TD":
                        if (typeof stack[0] === "number") state.lineX += stack[0] * state.scale;
                        if (typeof stack[1] === "number") state.y += stack[1];
                        if (tok.v === "TD" && typeof stack[1] === "number") state.leading = -stack[1] || 1;
                        state.moved = true;
                        break;
                    case "T*": state.y -= state.leading; state.moved = true; break;
                    case "Tm":
                        if (typeof stack[5] === "number") state.y = stack[5];
                        if (typeof stack[4] === "number") state.lineX = stack[4];
                        if (typeof stack[0] === "number") state.scale = Math.abs(stack[0]) || Math.abs(stack[1]) || 1;
                        state.moved = true;
                        break;
                    case "Do": {
                        const xobjects = isDict(resDict) ? resolve(resDict.XObject) : null;
                        const ref = isDict(xobjects) && typeof stack[0] === "string" ? xobjects[stack[0].slice(1)] : null;
                        if (!ref || ref.ref === undefined || visited.has(ref.ref) || depth >= 4) break;
                        visited.add(ref.ref);
                        const obj = objects.get(ref.ref);
                        const dict = valueOf(obj);
                        const form = isDict(dict) && dict.Subtype === "/Form" ? streamData(obj) : null;
                        if (form) {
                            state.moved = true;
                            run(form.toString("latin1"), dict.Resources !== undefined ? dict.Resources : res, depth + 1);
                        }
                        break;
                    }
                    case "BI": {
                        const id = /\sID\s/g;
                        id.lastIndex = lex.i;
                        if (id.exec(data)) {
                            const end = /\sEI(?=\s|$)/g;
                            end.lastIndex = id.lastIndex;
                            const found = end.exec(data);
                            lex.i = found ? end.lastIndex : data.length;
                        }
                        break;
                    }
                    default: break;
                }
                stack = [];
            }
        };

        const contents = resolve(page.Contents);
        const refs = Array.isArray(page.Contents) ? page.Contents : (Array.isArray(contents) ? contents : [page.Contents]);
        const chunks = refs.map(r => r && r.ref !== undefined ? streamData(objects.get(r.ref)) : null).filter(Boolean);
        if (chunks.length) run(chunks.map(c => c.toString("latin1")).join("\n"), resources, 0);
        return state.out;
    };

    const text = pages.map(page => {
        try { return extractPage(page); } catch { return ""; }
    }).join("\n\n");
    return text
        .normalize("NFKC")
        .replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/g, "")
        .replace(/[ \t]+/g, " ")
        .replace(/ ?\n ?/g, "\n")
        .replace(/\n{3,}/g, "\n\n")
        .trim();
}

module.exports = { extractPdfText };
