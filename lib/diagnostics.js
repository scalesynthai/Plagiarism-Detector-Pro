function citations(text) {
    const patterns = [
        /(?:\(|;\s*)([A-Z][\w'’–-]+(?:\s+(?:et\s+al\.|&\s*[A-Z][\w'’–-]+))?,\s*(?:19|20)\d{2}[a-z]?(?:,\s*p{1,2}\.?\s*\d+(?:[-–]\d+)?)?)(?=\s*[;)])/g,
        /\b[A-Z][a-zA-Z]+(?:\s+(?:et\s+al\.|and\s+[A-Z][a-zA-Z]+))?\s*\((?:19|20)\d{2}\)/g,
        /\[\d+(?:\s*[-–,]\s*\d+)*\]/g,
    ];
    return patterns.flatMap(p=>Array.from(text.matchAll(p), m=>m[0]));
}
const opening = /^\s*(?:#+\s*|\d+\.?\s*)?(abstract|introduction)\s*:?[ \t]*$/im;
const prose = /\b(?:this (?:paper|study|work)|we (?:hypothesi[sz]e|argue|propose|evaluate|investigate)|the central (?:claim|hypothesis|question)|model selection is)\b/i;
function selectOpening(text) {
    const heading = opening.exec(text), p = prose.exec(text);
    let start = 0, selection;
    if (heading) { start = heading.index+heading[0].length; selection=heading[1].toLowerCase(); }
    else if (p) { start=p.index; selection='opening prose'; }
    else {
        let offset=0, found=false;
        for (const paragraph of text.split(/\n\s*\n/)) {
            const position=text.indexOf(paragraph,offset); offset=position+paragraph.length;
            if (paragraph.trim().split(/\s+/).length>=20 && /[.!?]/.test(paragraph)) {start=position;found=true;break;}
        }
        if (!found) return {text:'',selection:'not located',start:0};
        selection='first substantial paragraph';
    }
    let rest=text.slice(start);
    const next=/^\s*(?:#+\s*|\d+\.?\s*)?(?:keywords|introduction|background|related work|modeling approach|methods?|methodology|results(?: and comparison)?|discussion|conclusion|references)\s*:?[ \t]*$/im.exec(rest);
    if(next) rest=rest.slice(0,next.index);
    return {text:rest.trim().slice(0,5000),selection,start};
}
function frontMatter(text) {
    const stops=[opening.exec(text),prose.exec(text)].filter(Boolean).map(m=>m.index);
    return text.slice(0,stops.length?Math.min(...stops):Math.min(text.length,1500));
}
module.exports={citations,selectOpening,frontMatter};
