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
- `deploy/compose.yaml`, `deploy/nginx.conf`: NAS 운영 설정
- `sitemap.xml`, `robots.txt`: 검색 엔진용 정보

로컬 웹 서버로 확인한 뒤 커밋을 푸시합니다. 공개 페이지에는 저장소 링크, 개인 포트폴리오, 확인되지 않은 고객사 또는 성과 수치를 표시하지 않습니다.

## NAS 배포

- 경로: `/volume1/docker/ryanfamily-site`
- 컨테이너: `ryanfamily-site` (재부팅 시 자동 시작)
- 웹 파일: `releases/<commit>/`, 현재 배포는 `releases/current` 심볼릭 링크로 선택합니다.
- 배포 대상: `index.html`, `styles.css`, `script.js`, `assets/`, `robots.txt`, `sitemap.xml`
- 컨테이너는 읽기 전용 파일 시스템과 일반 사용자 권한으로 실행하며, 포트는 NAS 내부에만 바인딩합니다.

업데이트 시 새 커밋의 배포 파일을 별도 릴리스 디렉터리에 가져오고 SHA-256을 확인한 후 `current` 링크를 교체합니다. 설정 변경 시 `docker compose run --rm --no-deps web -t`로 검사하고 `docker compose up -d`로 반영합니다. 기존 릴리스를 보존하면 `current`를 되돌려 복구할 수 있습니다. 자동 배포는 설정되어 있지 않습니다.
