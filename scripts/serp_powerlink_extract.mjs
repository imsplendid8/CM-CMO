/* serp_powerlink_extract.mjs — 네이버 SERP 파워링크 광고 구조화 추출(capture_serp.mjs·테스트 공용). */
// 파워링크 광고를 1건씩 구조화 추출 — 광고 1건 = "광고주 · 도메인 · 광고" 행 + 제목 + 설명 + 확장소재.
// 표시 도메인 요소를 기준점으로 삼아, 도메인이 1개만 들어 있는 가장 큰 조상을 광고 1건으로 본다.
// (링크에서 위로 올라가며 '광고' 글자를 찾던 이전 방식은 영역 머리글에서 멈춰 광고 본문을 놓쳤다.)
// 결과는 serp_observation_agent.py가 serp/ad_observations.json으로 정규화한다.
export async function extractPowerLinks(page) {
  return page.evaluate(() => {
    const DOMAIN=/^(?:https?:\/\/)?(?:[a-z0-9-]+\.)+(?:co\.kr|or\.kr|ne\.kr|kr|com|net|co|biz|io)(?:\/\S*)?$/i;
    const NOISE=/^(광고|도움말|이미지|신고하기|이미지 더보기|n ?pay|네이버페이|등록 안내|이 광고가 표시된 이유|정보확인.*|문서 저장하기|keep.*|·)$/i;
    const clean=s=>String(s||"").replace(/\s+/g," ").trim();
    // 네이버페이·로그인 배지 안내문(링크) — 제목으로 잡히면 안 된다
    const BADGE=/네이버 아이디|naver ?pay|npay 서비스|서비스 (보기|자세히)|네이버 로그인/i;
    const root=document.querySelector("#main_pack")||document.querySelector("#ct")||document.body;
    const domainLeaves=scope=>[...scope.querySelectorAll("a,span,cite,em,div")].filter(el=>!el.querySelector("a,span,cite,em,div")&&DOMAIN.test(clean(el.innerText)));
    // 광고 표식: '광고' 배지 또는 네이버 광고 클릭 링크(adcr/ader). 자연 검색결과가 광고로 섞이지 않게 항목마다 확인한다.
    const isAd=el=>/(^|\s)광고(\s|$)/.test(clean(el.innerText))||Boolean(el.querySelector('a[href*="adcr.naver"],a[href*="ader.naver"]'));
    // 파워링크 영역 머리글("○○ 관련 광고") — 상단·하단 영역 모두. '보험관련 광고이 정보가…' 같은 다른 박스는 제외
    const heads=[...root.querySelectorAll("h2,h3,strong,span,div")].filter(el=>{const t=clean(el.innerText);return t.length<=40&&/관련\s*광고(\s|$)/.test(t)});
    if(!heads.length)return [];
    const sections=[];
    for(const head of heads){
      let section=head;
      // 머리글에서 가장 가까운, 광고 도메인을 품은 조상 = 영역(광고 1건뿐인 하단 영역도 잡힌다)
      while(section&&section!==root&&!domainLeaves(section).length)section=section.parentElement;
      if(!section||section===root)continue;
      if(sections.some(x=>x.contains(section)||section.contains(x)))continue;
      sections.push(section);
    }
    if(!sections.length){
      // 도메인이 광고주명과 한 텍스트에 붙어 있는 마크업 — 영역 원문 줄을 넘기고 Python 쪽에서 광고별로 나눈다.
      let box=heads[0];
      while(box.parentElement&&box.parentElement!==root&&clean(box.innerText).length<300)box=box.parentElement;
      const lines=(box.innerText||"").split(/\n+/).map(clean).filter(t=>t&&!NOISE.test(t));
      return lines.length?[{kind:"powerlink",rank:0,raw:true,lines:lines.slice(0,200)}]:[];
    }
    const ads=[],seen=new Set();
    for(const section of sections)for(const leaf of domainLeaves(section)){
      let item=leaf;
      while(item.parentElement&&item.parentElement!==section&&domainLeaves(item.parentElement).length===1)item=item.parentElement;
      if(seen.has(item)||!isAd(item))continue;
      seen.add(item);
      const domain=clean(leaf.innerText).replace(/^https?:\/\//,"").replace(/\/.*$/,"").toLowerCase();
      const lines=(item.innerText||"").split(/\n+/).map(clean).filter(t=>t&&!NOISE.test(t)&&!BADGE.test(t));
      // 광고주명: 도메인 요소 직전의 텍스트 요소
      const texts=[...item.querySelectorAll("a,span,strong,em,div,p")].filter(el=>!el.querySelector("a,span,strong,em,div,p")).map(el=>clean(el.innerText)).filter(t=>t&&!NOISE.test(t)&&!BADGE.test(t));
      const di=texts.findIndex(t=>DOMAIN.test(t));
      const brand=di>0?texts[di-1]:"";
      const anchors=[...item.querySelectorAll("a")].map(a=>clean(a.innerText)).filter(t=>t&&!NOISE.test(t)&&!BADGE.test(t)&&t!==brand&&!DOMAIN.test(t));
      // 광고 원문은 [광고주] → [도메인] → [제목] → [설명] 순서 — 도메인 다음 줄을 제목으로 우선 사용
      const li=lines.findIndex(t=>t.toLowerCase().includes(domain));
      const lineTitle=li>=0&&lines[li+1]&&lines[li+1].length>=5?lines[li+1]:"";
      const title=lineTitle||anchors.find(t=>t.length>=8)||"";
      const rest=lines.filter(t=>t!==title&&t!==brand&&!DOMAIN.test(t)&&!t.includes(domain));
      const desc=rest.filter(t=>t.length>=20).sort((a,b)=>b.length-a.length)[0]||"";
      // 확장소재·하위링크는 링크 단위로(붙어 있는 칩이 한 줄로 합쳐지지 않게), 링크가 없으면 짧은 줄로 대체
      const shortAnchors=anchors.filter(t=>t!==title&&t!==desc&&t.length>=2&&t.length<=40);
      const extensions=[...new Set(shortAnchors.length?shortAnchors:rest.filter(t=>t!==desc&&t.length>=2&&t.length<=40))].slice(0,12);
      if(!title&&!desc)continue;
      ads.push({kind:"powerlink",rank:ads.length+1,brand,domain,title,desc,extensions,lines:lines.slice(0,20),hasImage:Boolean(item.querySelector("img"))});
      if(ads.length===20)break;
    }
    return ads;
  });
}
