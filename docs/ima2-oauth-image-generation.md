# ima2-gen OAuth 이미지 생성 연결

소재제작소의 썸네일·본문 이미지는 `ima2-gen`의 로컬 서버를 통해 생성할 수 있습니다.
이 연결은 **내 PC에서만 OAuth를 사용**하고, GitHub Pages나 저장소에는 OAuth 토큰을 복사하지 않는 방식입니다.

## 동작 구조

```text
소재제작소 이미지 큐
        ↓
scripts/generate_image_assets.py --provider ima2-oauth
        ↓  (127.0.0.1:3333, 로컬 호출)
ima2-gen /api/generate → GPT OAuth 세션
        ↓
PNG 검증 → assets/insurance/generated/<상품키>-*.png
        ↓
image-generation-queue.json 및 SERP 후보 asset 동기화
```

## Windows 최초 설정

PowerShell에서 아래 명령을 순서대로 실행합니다. `ima2 setup`에서 GPT OAuth를 선택하고,
브라우저 로그인은 본인 계정으로만 진행합니다.

```powershell
npx -y "@openai/codex" login
npx -y ima2-gen setup
npx -y ima2-gen serve
```

`ima2-gen serve`는 종료하지 말고 열린 상태로 둡니다. 기본 주소는 `http://127.0.0.1:3333`이며,
포트가 사용 중이면 생성기가 기록한 `~/.ima2/server.json`의 실제 포트를 자동으로 찾습니다.
그 다음 별도 PowerShell 창에서 실제 생성 큐를 실행합니다.

```powershell
$env:IMAGE_PROVIDER = "ima2-oauth"
$env:IMA2_SERVER_URL = "http://127.0.0.1:3333"
py -3 scripts/generate_image_assets.py --execute --provider ima2-oauth --product driver --limit 4
```

처음에는 `--limit 1`로 연결을 확인한 뒤 4건 단위로 늘리는 것을 권장합니다.
미리보기만 하려면 `--execute`를 빼면 됩니다. 이때는 API 호출과 파일 저장이 일어나지 않습니다.

## 소재제작소 Admin에서 확인할 것

Admin 우측의 **이미지 생성 연결 · ima2 OAuth** 상자에서 동일한 연결 명령을 복사할 수 있습니다.
Admin은 Pages에서 `localhost`를 호출하지 않습니다. HTTPS 페이지가 로컬 서버를 직접 호출하면
혼합 콘텐츠·CORS·토큰 노출 문제가 생길 수 있기 때문입니다. 생성이 끝나면 Admin을 새로고침해
큐의 `생성 완료`와 실제 썸네일을 확인합니다.

## 보안 원칙

- OAuth 토큰을 `TOUR_API_KEY`, GitHub Secret, `.env`, JSON 큐, 커밋에 넣지 않습니다.
- `ima2-oauth`는 루프백 주소(`127.0.0.1`, `localhost`, `::1`)만 허용합니다.
- GitHub Actions의 기존 `openai` 경로는 그대로 유지합니다. GitHub-hosted runner에는 개인 PC의
  ima2 OAuth 세션이 없으므로 Actions에서 OAuth를 실행하지 않습니다.
- 팀원이 공개 URL에서 보는 것은 커밋된 PNG와 공개 데이터뿐이며, OAuth 로그인 상태는 공유되지 않습니다.

## 실패 시 확인

1. `ima2-gen serve` 창이 실행 중인지 확인합니다.
2. `ima2 ping` 또는 `ima2 doctor`로 로컬 설치 상태를 확인합니다.
3. 다른 포트를 사용했다면 `--ima2-url http://127.0.0.1:<포트>`로 지정합니다.
4. `OPENAI_API_KEY Secret이 없습니다`가 나오면 provider가 `openai`로 실행된 것입니다. 명령에
   `--provider ima2-oauth`를 넣거나 `IMAGE_PROVIDER` 환경변수를 확인합니다.
5. 생성 실패 항목은 큐에 `failed`와 `last_error`로 남습니다. 원인을 해결한 뒤
   `--retry-failed`로 실패 항목만 다시 시도할 수 있습니다.

생성기는 상품별 큐 prompt를 보존하면서 텍스트·숫자·로고·워터마크·다른 보험종목 오브젝트를
제외하고, 텍스트 없는 프리미엄 3D 애니메이션 스타일을 한 번 더 고정합니다.
