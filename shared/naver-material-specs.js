(function (root) {
  "use strict";

  const freeze = (value) => Object.freeze(value);
  const spec = freeze({
    verifiedAt: "2026-08-25",
    guideUrl: "https://ads.naver.com/adguide?categorySeq=160",
    publicGuide: freeze({
      additionalTitle: "파워링크 제목 등록기준 준용",
      promotion: "파워링크 설명문구 등록기준 준용",
      sublink: "사이트당 최대 4개이며 서브링크명과 실제 연결 URL이 일치해야 함",
      calculation: "금융·보험 업종에서 조건별 가격 시뮬레이션 기능이 있는 URL만 사용",
    }),
    base: freeze({ titleMax: 15, descriptionMin: 20, descriptionMax: 45 }),
    extension: freeze({
      additionalTitle: freeze({ maxLength: 15, maxPerGroup: 15 }),
      additionalDescription: freeze({ maxLength: 45, maxPerGroup: 4 }),
      promotion: freeze({ maxLength: 14, maxPerGroup: 2 }),
      sublink: freeze({ nameMaxLength: 6, minPerAd: 3, maxPerAd: 4, maxPerSite: 4 }),
    }),
    powerContentEditorial: freeze({ titleMin: 7, titleMax: 28, descriptionMin: 80, descriptionMax: 110 }),
    manualOnlyFields: freeze([
      "calculationUrl",
      "powerLinkImageId",
      "sublinkUrl1",
      "sublinkUrl2",
      "sublinkUrl3",
      "sublinkUrl4",
      "sublinkImageId1",
      "sublinkImageId2",
      "sublinkImageId3",
      "sublinkImageId4",
    ]),
  });

  root.ModooNaverMaterialSpecs = spec;
})(globalThis);
