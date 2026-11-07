# 우리반 디지털 시민 마을 갤러리

작품 링크·포스터 등록, 댓글, 4가지 반응, 검색과 정렬, SSE 실시간 갱신을 제공하는 Python 3 앱입니다.

## 권장 공개 배포: Render + Supabase

[가입·설정·데이터 이전 안내](deploy/RENDER_SUPABASE.md)를 따르세요. `render.yaml`에 Render 설정, `supabase/schema.sql`에 DB 및 Storage 설정이 있습니다. `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `GALLERY_BACKEND=supabase`를 서버 환경변수에 설정합니다. Supabase 키는 브라우저로 전달하지 않습니다.

기존 데이터 이전: `python3 deploy/migrate_supabase.py --source data/gallery.db`. 동일한 ID는 건너뛰며 원본과 기존 댓글을 보존합니다. 서버 재시작 때 자동으로 반복하지 않습니다. 이미지 업로드 후 DB 쓰기가 실패한 경우 재시도할 수 있으며, 실패한 등록의 사용되지 않는 Storage 파일은 별도 정리가 필요할 수 있습니다.

## 로컬 개발

```sh
python3 server.py
```

기본은 SQLite이며 `data/gallery.db`를 사용합니다. `GALLERY_DATA_DIR`, `PORT`로 경로와 포트(기본 8080)를 변경할 수 있습니다. Python 표준 라이브러리만 사용합니다. `GALLERY_BACKEND=supabase`이면 로컬 디스크 대신 Supabase를 사용하며, 잘못된 설정 시 로컬 DB로 자동 전환하지 않습니다.

작품의 웹사이트 링크를 등록하는 방식입니다. 웹사이트 파일 자체의 호스팅은 별도로 해야 합니다. 반응은 브라우저 식별자별로 구분하며 작품 등록에는 수업용 비밀번호, 작품 삭제에는 별도의 선생님 비밀번호가 필요합니다. 학급별 접근 제한은 아직 없습니다. 실시간 알림을 위해 서버 인스턴스는 1개로 운영합니다.

## 검증

`python3 -m unittest discover -s tests -v`

로컬 동시 저장과 모의 Supabase 요청·재이전 보존을 검증합니다. 실제 Supabase 통합 검증에는 별도 프로젝트가 필요합니다. 브라우저 3개를 이용한 등록·반응·댓글·작성 내용 유지·재시작 시나리오는 로컬 SQLite 경로에서 통과했습니다.

기존 Python 서버 + 영구 디스크 방식은 `deploy/README.md`의 대안 구성입니다. 현재 선택한 Render + Supabase 배포에는 그 디스크 설정이나 `deploy/start.sh`를 사용하지 않습니다.

## 등록 비밀번호와 작품 삭제

Render 서비스 → Environment에 `GALLERY_REGISTRATION_PASSWORD`(학생에게 알려줄 등록 비밀번호), `GALLERY_ADMIN_PASSWORD`(선생님 전용 삭제 비밀번호)를 서로 다른 값으로 설정하고 Save, rebuild, and deploy를 실행하세요. 비밀번호가 설정되지 않으면 해당 작업은 거부됩니다. 열람·댓글·반응은 비밀번호 없이 가능합니다.

오른쪽 위 ‘선생님’을 누르면 각 작품의 삭제 버튼이 표시됩니다. 버튼 표시는 권한 부여가 아니며 실제 삭제 요청마다 서버가 선생님 비밀번호를 검증합니다. 삭제 확인 창에서 제목을 확인하고 선생님 비밀번호를 입력하세요. 작품·댓글·반응이 함께 삭제되고 모든 접속 화면에 반영됩니다. 포스터도 삭제를 시도하며 Storage 연결 실패 시 잔여 파일은 별도 정리가 필요할 수 있습니다. 삭제는 되돌릴 수 없습니다.

비밀번호를 DB나 브라우저 저장소에 저장하지 않습니다. 환경변수에서 바꾸면 새 배포부터 변경된 비밀번호가 적용됩니다. Supabase 삭제 권한은 실제 프로젝트에서 확인했습니다. 다른 프로젝트에서 권한 오류가 발생하면 `supabase/enable_deletion.sql`을 실행하세요.
