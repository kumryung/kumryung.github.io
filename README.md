# RyanFamily · 라이언패밀리

CRM 및 게임 개발 회사 라이언패밀리의 공식 소개 사이트입니다.

- 공식 주소: https://www.ryanfamily.xyz/
- 문의: ryan@ryanfamily.xyz
- 순수 HTML, CSS, JavaScript로 구성된 반응형 정적 사이트입니다.
- 별도의 패키지 설치나 빌드가 필요하지 않습니다.
- GitHub는 소스 보관용이며, 실제 사이트는 NAS의 Nginx 컨테이너에서 제공합니다.
- Cloudflare의 기존 `synology` 터널이 HTTPS를 제공하며 NAS의 `127.0.0.1:4330`으로 연결합니다.
- 고객 데이터 수집 폼이나 분석 추적 코드를 사용하지 않습니다. 이메일 링크는 방문자의 메일 앱을 엽니다.

## 수정

- `index.html`: 회사 소개, 개발 분야, 문의 정보 및 검색 메타데이터
- `styles.css`: 반응형 레이아웃과 브랜드 스타일
- `script.js`: 모바일 메뉴와 이메일 주소 복사
- `assets/`: 파비콘과 소셜 공유 이미지
- `assets/products/`: 공개용 데모 CRM 3장과 개발 중인 게임 4장의 실제 화면
- `deploy/compose.yaml`, `deploy/nginx.conf`: NAS 운영 설정
- `sitemap.xml`, `robots.txt`: 검색 엔진용 정보

로컬 웹 서버로 확인한 뒤 커밋을 푸시합니다. 공개 페이지에는 저장소 링크, 개인 포트폴리오, 확인되지 않은 고객사 또는 성과 수치를 표시하지 않습니다.

개발 분야에는 Web CRM(아동발달센터 통합 관리)과 ‘어서 와, 용의 둥지에’를 개발 중으로 소개합니다. 화면은 2026-10-08 실제 브라우저에서 촬영했습니다. CRM 데이터는 사용자가 공개 가능한 가상 데모 데이터임을 확인했습니다. 게임은 소스 0.2.51의 실행 중인 개발 미리보기에서 메인·둥지·던전·도입부를 촬영했으며, 홈페이지 갱신이 게임 운영 버전의 배포를 의미하지는 않습니다. 화면 링크는 확대 창과 키보드 좌우 탐색을 지원하고, JavaScript가 없으면 원본 이미지를 엽니다.

## NAS 배포

- 경로: `/volume1/docker/ryanfamily-site`
- 컨테이너: `ryanfamily-site` (재부팅 시 자동 시작)
- 웹 파일: `releases/<commit>/`, 현재 배포는 `releases/current` 심볼릭 링크로 선택합니다.
- 배포 대상: `index.html`, `styles.css`, `script.js`, `assets/`, `robots.txt`, `sitemap.xml`
- 컨테이너는 읽기 전용 파일 시스템과 일반 사용자 권한으로 실행하며, 포트는 NAS 내부에만 바인딩합니다.

업데이트 시 새 커밋의 배포 파일을 별도 릴리스 디렉터리에 가져오고 SHA-256을 확인한 후 `current` 링크를 교체합니다. 설정 변경 시 `docker compose run --rm --no-deps web -t`로 검사하고 `docker compose up -d`로 반영합니다. 기존 릴리스를 보존하면 `current`를 되돌려 복구할 수 있습니다. 자동 배포는 설정되어 있지 않습니다.

## 홈페이지 방문 알림

NAS의 `ryanfamily-visit-notifier`가 Nginx 방문 기록을 읽어 지정된 텔레그램 채팅에 알림을 보냅니다. `www.ryanfamily.xyz`의 HTTPS 홈페이지 GET 요청 중 성공한 200/304 응답을 대상으로 하며, 정적 이미지·CSS·스크립트·상태 검사·실패 요청은 제외합니다. Cloudflare가 제공하는 `CF-Connecting-IP`를 사용하고, 원본 Nginx 포트는 기존처럼 NAS loopback에만 공개합니다.

같은 IP의 **마지막 방문 후 600초 미만**이면 중복 알림을 생략하고 마지막 방문 시각을 갱신합니다. 600초 이상 방문이 없었다면 다음 방문에 다시 알립니다. IPv4/IPv6를 정규화하며, 사용자 식별이나 사람/봇 판별을 하지 않습니다. 알림에는 IP, 한국 시간, 공식 홈페이지 주소만 넣습니다. 요청 쿼리·쿠키·계정 정보는 수집하거나 보내지 않습니다.

- `.secrets/telegram_bot_token`, `.secrets/telegram_chat_id`: NAS에만 저장하고 Compose secret으로 읽습니다. 소스·공개 페이지·로그에 값을 넣지 않습니다.
- `visitor-logs/`: 날짜별 로그. 끝까지 처리한 파일은 마지막 기록 후 48시간이 지나면 정리합니다.
- `.notifier-state/`: SQLite의 읽기 위치, 10분 중복 판단, 전송 대기열을 보존합니다. 재시작해도 처리된 로그를 다시 알리지 않습니다.
- 전송 실패는 대기열에서 지수 간격으로 재시도하며 Telegram 429의 대기 시간을 따릅니다. 전송 응답 유실 시에는 Telegram의 API 특성상 드물게 중복 전송될 수 있습니다.

최초 구성 시 `visitor-logs/`와 `.notifier-state/`를 UID/GID 101 소유의 0700 디렉터리로 준비합니다. `.secrets/`는 0700, 두 secret 파일은 UID/GID 101 소유 0400으로 둡니다. `deploy/visit_notifier.py`를 NAS 배포 루트에 함께 반영합니다. 기존 처리 기록과 대기열은 업데이트 시 지우지 않습니다.

검사: `python -B -m unittest discover -s deploy -p 'test_*.py' -v`. 운영 로그는 `docker logs --tail 20 ryanfamily-visit-notifier`로 준비/전송/재시도 상태만 확인합니다. 알림 중지는 해당 notifier 컨테이너만 중지하면 됩니다.

구현 참고: [Nginx access log](https://nginx.org/en/docs/http/ngx_http_log_module.html), [Telegram sendMessage](https://core.telegram.org/bots/api#sendmessage).
