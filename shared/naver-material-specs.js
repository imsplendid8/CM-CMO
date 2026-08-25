(function (root) {
  "use strict";

  const freeze = (value) => Object.freeze(value);
  const spec = freeze({
    verifiedAt: "2026-08-25",
    guideUrl: "https://ads.naver.com/adguide?categorySeq=160",
    powerContentGuideUrl: "https://ads.naver.com/help/faq/597",
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
      image: freeze({
        width: 214,
        height: 214,
        maxBytes: 5242880,
        fileTypes: freeze(["image/jpeg", "image/png"]),
        powerLinkMax: 1,
        imageSublinkMax: 3,
        sourceUrl: "https://naver.github.io/searchad-apidoc/release/2025/06/25/release-note/",
      }),
    }),
    powerContent: freeze({
      title: freeze({ minLength: 7, maxLength: 28 }),
      description: freeze({ minLength: 80, maxLength: 110, source: "landing_continuous_excerpt" }),
      businessName: freeze({ minLength: 1, maxLength: 20 }),
      image: freeze({ minPixels: 400, maxPixels: 2000, fileTypes: freeze(["BMP", "JPEG", "JPG"]) }),
      maxPerAdGroup: 5,
    }),
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
    ]),
  });

  root.ModooNaverMaterialSpecs = spec;
})(globalThis);
