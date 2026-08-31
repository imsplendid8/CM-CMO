# 이미지 생성 공급자 연결

현재 `data/adcopy/image-generation-queue.json`의 37건은 **대기(pending)** 상태다.
장면·상품키·프롬프트는 준비됐지만 실제 PNG 파일이 아직 없다는 뜻이며, 실패한
상태가 아니다. 기존 이미지 8건은 이미 `assets/insurance/generated/`에 저장돼 있다.

## 권장 공급자

OpenAI Images API를 기본 어댑터로 연결했다. API 응답의 `b64_json` 이미지를 PNG로
저장하고, URL 응답도 HTTPS인 경우에만 보조적으로 내려받는다. OpenAI API 키는
브라우저나 저장소에 넣지 않고 GitHub Secret으로만 사용한다. 이미지 API는 생성된
이미지를 base64로 반환할 수 있다([공식 API 참고](https://platform.openai.com/docs/api-reference/images-streaming/image_generation/partial_image)).

## GitHub 설정

1. OpenAI API 키를 발급하고 결제·사용 한도를 확인한다.
2. GitHub 저장소의 `Settings → Secrets and variables → Actions`에서
   `OPENAI_API_KEY` Secret을 만든다. 키를 채팅·코드·로그에 붙여 넣지 않는다.
3. (선택) Repository Variables에 다음 값을 넣어 모델과 품질을 조정한다.

```text
OPENAI_IMAGE_MODEL=gpt-image-1
OPENAI_IMAGE_SIZE=1024x1024
OPENAI_IMAGE_QUALITY=medium
```

## 실행 순서

Actions → **Generate Image Assets** → `Run workflow`에서 다음 순서로 실행한다.

1. `execute=false`, `limit=4`, `product=driver`처럼 먼저 미리보기로 범위를 확인한다.
2. 같은 범위에서 `execute=true`로 실행한다. 이때만 API 호출과 비용이 발생한다.
3. 이전 실행에서 `failed`가 남았다면 `retry_failed=true`를 선택해 해당 항목만 다시 시도한다.
4. 생성 후 PNG 헤더·정사각형·214px 이상·5MB 이하·상품별 파일 경로 검사를 한다.
5. 검사를 통과한 파일만 계획의 `asset`으로 반영되고, Pages가 새 PNG를 배포한다.
6. 실패한 항목은 `failed`와 오류 요약이 큐에 남는다. 다음 실행에서 `retry_failed=true`로 재시도할 수 있다.

한 번에 생성할 수 있는 범위는 1~20건이다. API 오류가 일부 발생해도 실패 상태를
큐에 커밋하고 Pages에 반영하도록 워크플로가 경고로 종료한다. 잘못된 이미지 파일이나
검증 오류가 있으면 커밋하지 않고 작업을 실패시킨다. 사용자 지정 API URL은 키가
평문으로 전송되지 않도록 HTTPS만 허용한다.

기본 배치는 4건이다. 스타일·상품 혼입을 먼저 확인한 뒤 상품별로 나눠 실행하면
37건을 한 번에 생성하는 비용과 검수 부담을 줄일 수 있다.

## 로컬 점검

API를 호출하지 않는 안전한 미리보기:

```bash
python scripts/generate_image_assets.py --limit 4 --product driver
```

실제 생성은 키가 있는 비공개 환경에서만 다음처럼 실행한다.

```bash
OPENAI_API_KEY=... python scripts/generate_image_assets.py --execute --limit 4 --product driver
```

Windows PowerShell에서는 `$env:OPENAI_API_KEY`를 사용하고 명령 실행 후 바로
환경변수를 지운다. 생성 파일은 `scripts/image_generation_queue.py --sync`와
`node scripts/check_adcopy_images.mjs`를 모두 통과해야 배포 대상이 된다.

## 비용·보안 경계

- 월간 계획 워크플로는 API를 호출하지 않고 큐만 만든다.
- 생성 워크플로는 예약 실행하지 않으며, 운영자가 `execute=true`를 선택해야 한다.
- API 키와 응답 원문은 커밋하지 않는다. PNG만 상품별 공개 asset으로 커밋한다.
- 이미지에 텍스트·숫자·로고·워터마크·다른 보험종목 오브젝트가 들어가지 않았는지
  사람 검수를 거친다. 자동 검사는 파일 형식과 연결 관계만 보장한다.
