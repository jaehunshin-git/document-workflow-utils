# document-workflow-utils

[![CI](https://github.com/jaehunshin-git/document-workflow-utils/actions/workflows/ci.yml/badge.svg)](https://github.com/jaehunshin-git/document-workflow-utils/actions/workflows/ci.yml)

> 흩어진 파일 목록의 누락·중복·구조를 한 번에 검증하는 무의존성 Python CLI

회사생활에서 접한 반복적인 파일 검증 문제를 일반화해 개인적으로 다시 구현한 포트폴리오입니다. 사람이 눈으로 대조하던 숫자·파일명·디렉터리 구조 검사를 `doc-utils`라는 일관된 명령 체계로 묶고, 텍스트와 JSON 출력 및 명확한 종료 코드로 자동화에 연결할 수 있게 만들었습니다.

이 저장소에는 외부 조직의 코드, 데이터, 로고와 내부 경로가 포함되어 있지 않습니다. 모든 예제와 테스트 데이터는 이 프로젝트를 위해 만든 합성 자료입니다.

## ✨ 주요 기능

| 기능 | 해결하는 문제 |
| --- | --- |
| `numbers` | 연속된 정수 목록에서 누락·중복·비정상 행을 찾습니다. |
| `duplicates` | 텍스트 목록의 중복 항목과 등장 횟수를 결정적 순서로 집계합니다. |
| `compare` | 기대 파일과 실제 디렉터리를 재귀 비교하고 누락·추가 항목을 보고합니다. |
| `tree` | 디렉터리 구조를 text/emoji 트리와 부모 경로 CSV로 표현합니다. |
| JSON 출력 | 모든 명령 결과를 후속 자동화가 소비할 수 있는 구조로 제공합니다. |
| Ignore 패턴 | 임시 파일과 불필요한 경로를 반복 가능한 패턴으로 제외합니다. |

### 30초 데모

저장소에 포함된 합성 데이터로 바로 실행할 수 있습니다.

```bash
$ uv run doc-utils numbers examples/numbers.txt
유효 정수: 5
비정상 행: 1
누락 값 수: 2
중복 값 수: 1
범위: 100 ~ 105
누락 값: 102, 104
중복 값: 103

$ uv run doc-utils compare examples/expected-files.txt examples/documents --ignore '*.tmp'
기대 파일 수: 3
실제 파일 수: 2
누락 파일 수: 1
누락 파일:
inbox/report-c.txt
예기치 않은 파일 수: 0
예기치 않은 파일:
```

자동화에서는 같은 결과를 JSON으로 받을 수 있습니다.

```bash
uv run doc-utils numbers examples/numbers.txt --json
uv run doc-utils tree examples/documents --ignore '*.tmp' --json
```

## 🧭 설계 방향

- **예측 가능한 결과:** 모든 목록을 결정적으로 정렬해 로컬·CI의 출력 차이를 줄였습니다.
- **안전한 탐색:** 심볼릭 링크와 운영체제 메타데이터를 제외해 순환과 루트 이탈을 방지했습니다.
- **자동화 친화성:** JSON 출력과 의미가 구분된 종료 코드로 셸·CI 파이프라인에 연결합니다.
- **작은 공급망:** 런타임 외부 의존성 없이 Python 표준 라이브러리만 사용합니다.
- **공개 경계:** 독립 구현 원칙과 합성 데이터 정책을 문서로 남겨 포트폴리오의 출처를 설명합니다.

## 🛠 기술 스택

| Category | 기술 |
| --- | --- |
| Language | Python 3.11+ |
| Runtime | Python 표준 라이브러리, 외부 의존성 0개 |
| Package Management | uv |
| Build | Hatchling |
| Testing & Quality | pytest, Ruff, GitHub Actions |
| Interface | Python API, CLI (`doc-utils`), JSON |

## 🔍 기술 선정 이유

| 구분 | 기술 | 선정 이유 |
| --- | --- | --- |
| 실행 환경 | 표준 라이브러리 | 설치 비용과 공급망 노출을 줄이고 작은 CLI의 이식성을 높입니다. |
| 패키지 관리 | uv | 잠금 파일을 바탕으로 개발·CI 환경을 빠르게 재현합니다. |
| 품질 | pytest · Ruff | 경계 조건을 회귀 테스트하고 일관된 코드 품질을 검사합니다. |
| 자동화 | GitHub Actions | Python 3.11–3.13에서 테스트·정적 검사·빌드를 반복 검증합니다. |

세부 선택과 트레이드오프는 [설계 의사결정](docs/decisions.md)에 기록했습니다.

## 📁 프로젝트 구조

```text
document-workflow-utils/
├── src/document_workflow_utils/  # 공개 API와 CLI 구현
├── tests/                        # 합성 데이터 기반 회귀 테스트
├── examples/                     # 바로 실행 가능한 합성 입력과 디렉터리
├── docs/                         # 설계 결정과 출처 경계
├── .github/workflows/            # Python 버전별 자동 검증
└── pyproject.toml                # 패키지·품질 도구 설정
```

## 🚀 시작하기

### 요구 사항

- Python 3.11 이상
- [uv](https://docs.astral.sh/uv/)

### 1. 저장소 내려받기

```bash
git clone https://github.com/jaehunshin-git/document-workflow-utils.git
cd document-workflow-utils
```

### 2. 설정하기

런타임 외부 의존성은 없습니다. 테스트와 정적 검사 도구를 포함한 개발 환경은 다음 명령으로 재현합니다.

```bash
uv sync --locked
```

### 3. 실행하기

```bash
uv run doc-utils --version
uv run doc-utils numbers examples/numbers.txt
uv run doc-utils duplicates examples/names.txt --json
uv run doc-utils compare examples/expected-files.txt examples/documents --ignore '*.tmp'
uv run doc-utils tree examples/documents --mode emoji --ignore '*.tmp'
```

`--ignore`는 `compare`와 `tree`에서 반복할 수 있습니다. `--json`은 모든 하위 명령에서 사용할 수 있습니다.

| 종료 코드 | 의미 |
| --- | --- |
| `0` | 정상 처리. `compare`에서 추가 파일만 발견한 경우도 포함합니다. |
| `1` | 유효한 정수가 없거나 기대 파일이 누락되었습니다. |
| `2` | 명령 사용 또는 입출력 오류입니다. |

### 4. 검증하기

```bash
uv run pytest
uv run ruff check src tests
uv build
```

## 📚 문서

| 문서 | 내용 |
| --- | --- |
| [설계 의사결정](docs/decisions.md) | 정렬·탐색·종료 코드·보안 경계의 선택 이유 |
| [출처 및 구현 경계](docs/provenance.md) | 독립 구현 원칙과 합성 데이터 정책 |

## 🤝 협업 규칙

### Branch

`<type>/<topic>`

```text
feat/json-output
```

### Commit Message

`<type>(<scope>): <한국어 요약>`

```text
feat(cli): JSON 출력 형식 추가
```

## 📄 이용 안내

이 저장소는 오픈소스 라이선스를 제공하지 않으며, 모든 권리를 유보합니다. 명시적인 사전 허가 없이 이 저장소의 코드와 문서를 복제, 수정, 재배포하거나 상업적으로 이용할 수 없습니다.
