# 합성 파일 인수 검증 시나리오

이 시나리오는 전달받아야 할 문서 목록과 실제 디렉터리를 자동으로 대조하는 흐름을 보여 줍니다. 입력 파일과 디렉터리는 모두 이 프로젝트를 위해 만든 합성 데이터입니다.

## 상황

세 개의 보고서가 전달되어야 하지만 실제 디렉터리에는 두 개만 있습니다. 작성 중인 `draft.tmp`는 검증 대상에서 제외해야 합니다.

```text
expected-files.txt              documents/
archive/report-b.txt            ├── archive/
inbox/report-a.txt              │   └── report-b.txt
inbox/report-c.txt              └── inbox/
                                    ├── draft.tmp
                                    └── report-a.txt
```

## 1. 사람이 결과 확인하기

```bash
uv run doc-utils compare examples/expected-files.txt examples/documents --ignore '*.tmp'
```

도구는 `inbox/report-c.txt`가 누락되었다고 보고하고 종료 코드 `1`을 반환합니다. 셸이나 CI는 이 값을 이용해 다음 작업으로 넘어가지 않게 할 수 있습니다.

## 2. JSON을 후속 자동화에서 소비하기

아래 예제는 동일한 비교 결과를 JSON으로 읽고 누락 파일만 요약합니다.

```bash
uv run python examples/verify_manifest.py
```

예상 출력은 다음과 같습니다.

```text
검증 실패: 누락 파일 1개
- inbox/report-c.txt
```

예제 소비 코드는 `doc-utils`의 종료 코드 `0`, `1`, `2`를 구분하며, JSON의 `schema_version`도 확인합니다. 따라서 명령 실행 실패와 파일 검증 실패를 서로 다른 상황으로 처리할 수 있습니다.

## 3. 엄격한 인수 검사 적용하기

추가 파일까지 오류로 취급해야 하는 CI에서는 `--strict`를 사용합니다.

```bash
uv run doc-utils compare examples/expected-files.txt examples/documents \
  --ignore '*.tmp' \
  --strict \
  --json
```

기본 모드는 추가 파일을 보고하되 성공으로 처리하고, 엄격 모드는 누락과 추가를 모두 실패로 처리합니다. 이 정책 차이는 탐색용 보고와 자동화된 인수 검사를 같은 도구로 지원하기 위한 선택입니다.
