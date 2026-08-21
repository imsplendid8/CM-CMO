(function(root){
"use strict";
/* im-not-ai humanize-korean light 원칙의 브라우저용 보수 후처리.
   숫자·날짜·인용·상품명은 건드리지 않고 명백한 이중 피동과 기계적 쉼표만 정리한다.
   Upstream inspiration (MIT): https://github.com/epoko77-ai/im-not-ai */
const RULES=[
  [/도출되어진/g,"도출된"],[/판단되어진/g,"판단된"],[/결정되어진/g,"결정된"],
  [/작성되어진/g,"작성된"],[/생성되어진/g,"생성된"],[/사용되어진/g,"사용된"],
  [/보여질 수/g,"보일 수"],[/되어져/g,"돼"],
];
function light(value){
  const src=String(value==null?"":value).trim();let out=src;
  RULES.forEach(([re,to])=>{out=out.replace(re,to);});
  out=out.replace(/([가-힣]{2,}(?:지만|면서|아서|어서|으며|이고|하고)),\s+/g,"$1 ").replace(/[ \t]{2,}/g," ");
  // 단순 길이 변화가 30%를 넘으면 과윤문으로 보고 원문을 쓴다.
  return src&&Math.abs([...src].length-[...out].length)/[...src].length>.30?src:out;
}
function excerpt(value,limit){
  const s=light(value),chars=[...s],floor=Math.floor(limit*.5);
  if(chars.length<=limit&&(/\p{Sentence_Terminal}$/u.test(s)||chars.length<floor))return s;
  if(chars.length<=limit){
    const sentence=Math.max(s.lastIndexOf("."),s.lastIndexOf("!"),s.lastIndexOf("?"));
    if(sentence>=Math.min(20,floor))return s.slice(0,sentence+1);
    const clause=Math.max(s.lastIndexOf(","),s.lastIndexOf("·"),s.lastIndexOf(";"),s.lastIndexOf("→"));
    return (clause>=floor?s.slice(0,clause):s).replace(/[ ,·]+$/g,"").replace(/\s+\d[\d.,]*$/g,"")+"…";
  }
  const part=chars.slice(0,limit+1).join("");
  const sentence=Math.max(part.lastIndexOf("."),part.lastIndexOf("!"),part.lastIndexOf("?"));
  if(sentence>=floor)return part.slice(0,sentence+1);
  let cut=part.lastIndexOf(" ");
  if(cut<floor)cut=limit;
  return [...part].slice(0,cut).join("").replace(/[ ,·]+$/g,"").replace(/\s+\d[\d.,]*$/g,"")+"…";
}
root.ModooHumanizeKo={light,excerpt,source:"epoko77-ai/im-not-ai · light-compatible"};
})(globalThis);
