# Render + Supabase: 가입부터 공개 배포까지

이 구성은 Render의 로컬 디스크에 작품을 저장하지 않습니다. 작품·댓글·반응은 Supabase PostgreSQL에, 포스터는 Supabase Storage에 저장합니다. 브라우저는 Render 서버의 API와 SSE에 연결합니다. Supabase Realtime 기능을 별도로 켤 필요는 없습니다. Render 서버 인스턴스는 1개로 유지합니다.

## 1. 계정과 프로젝트 만들기

1. https://supabase.com 에서 가입하고 New project를 선택합니다. 프로젝트 이름은 `digital-citizen-gallery` 등으로 정합니다. 데이터베이스 암호는 안전하게 보관하고 채팅에 보내지 않습니다. 가까운 지역을 선택합니다.
2. 프로젝트가 준비되면 Project URL을 확인합니다. `https://프로젝트ID.supabase.co` 형태이며 공개 식별 정보입니다. 이 URL은 설정 지원을 위해 공유할 수 있습니다.
3. https://render.com 에서 가입하고 GitHub 계정을 연결합니다. 이 단계에서는 유료 디스크를 추가하지 않습니다. 각 서비스의 현재 무료 한도와 요금은 가입 화면에서 확인합니다.

## 2. Supabase 데이터베이스 준비

SQL Editor에서 이 프로젝트의 `supabase/schema.sql` 전체를 실행합니다. 작품 테이블, 동시 수정용 함수, 포스터 버킷을 만듭니다. 테이블은 RLS를 사용하며 익명 클라이언트의 직접 쓰기를 허용하지 않습니다. 포스터 버킷은 갤러리에 표시하도록 공개 읽기를 허용합니다.

프로젝트 설정의 API Keys에서 서버용 Secret key (`sb_secret_...`) 또는 legacy `service_role` 키를 확인합니다. **publishable/anon 키는 사용할 수 없습니다.** 이 서버용 키를 HTML, GitHub, 채팅에 넣지 않습니다. 프로젝트 URL과 서버용 키는 아래의 보안 환경변수 입력란에만 설정합니다.

## 3. Render 배포

현재 변경한 서버 파일들이 GitHub 저장소에 반영된 다음 진행합니다. 이 작업공간의 변경은 자동으로 GitHub에 반영되지 않습니다.

Render에서 New → Blueprint로 해당 저장소를 선택하면 `render.yaml`을 읽습니다. 아래 값을 Render의 환경변수 입력란에 설정합니다.

| 이름 | 값 |
|---|---|
| `GALLERY_BACKEND` | `supabase` (설정 파일에 포함) |
| `SUPABASE_URL` | 프로젝트의 HTTPS URL |
| `SUPABASE_SERVICE_ROLE_KEY` | 서버용 Secret key 또는 service_role 키 |

시작 명령은 `python server.py`, 빌드는 표준 라이브러리 구문 검사, 상태 확인 경로는 `/healthz`입니다. 별도의 영구 디스크나 Python 패키지 설치는 필요하지 않습니다. `PORT`는 Render가 제공합니다. Supabase 연결에 실패하면 상태 확인이 실패하며, 빈 로컬 DB로 우회하지 않습니다.

## 4. 기존 작품 이전

Render에 소스 코드만 올려서는 기존 작품이 자동으로 생기지 않습니다. 제공된 배포 압축 파일의 `backup/gallery.db`를 사용해 아래 명령을 **한 번** 실행해야 합니다. 실행할 머신의 안전한 환경 설정에 위 Supabase URL과 키가 등록되어 있어야 합니다.

```sh
python3 deploy/migrate_supabase.py --source backup/gallery.db
```

이 작업공간에서 실행한다면 소스 경로는 `data/gallery.db`입니다. 연결이 준비되면 도우미가 기존 작품을 이전하고 확인할 수 있습니다. 이미지 4개를 Storage에 업로드하고 작품·댓글·반응을 DB에 등록합니다. 같은 명령을 다시 실행해도 기존 ID는 건너뛰어 운영 중인 댓글과 반응을 덮어쓰지 않습니다. 원본 SQLite 파일은 읽기 전용으로 열어 보존합니다. 백업을 Git에 올릴 필요는 없습니다.

## 5. 공개 주소에서 최종 확인

Render가 발급한 HTTPS 주소를 사용합니다. 처음 이전한 직후 작품 4개, 포스터 4개, 댓글 12개, 반응 14개인지 확인합니다. 독립된 브라우저 두 개에서 한쪽의 작품 등록·댓글·반응이 다른 쪽에 바로 표시되는지 확인합니다. Render 재시작 후에도 데이터가 남아 있어야 합니다.

무료 서비스는 정책에 따라 휴면·시작 지연·용량 제한이 있을 수 있습니다. 수업 전 실제 주소에 접속해 상태를 확인하세요. 이 구성은 영구 디스크 비용을 없애지만 서비스의 영구 무료나 무제한 사용을 보장하지 않습니다.

## 현재 검증 범위

- 로컬 SQLite 경로: 독립 브라우저 3개의 등록·댓글·좋아요·실시간 반영·재시작 검증 통과.
- 저장소 어댑터: 이미지 업로드 요청, 서버용 키 헤더, 오류 메시지 비밀정보 제외, 재이전 시 기존 데이터 보존을 모의 Supabase 응답으로 검증.
- 동시 반응·댓글 30건씩 로컬 저장 검증 통과.
- 실제 Supabase SQL 실행·Storage 업로드·Render 배포·HTTPS 접속은 계정과 프로젝트가 아직 없어 미실행. 모의 검증은 실제 서비스 검증을 대체하지 않습니다.
