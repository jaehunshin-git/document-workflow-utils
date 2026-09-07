# document-workflow-utils

> 파일 목록 비교와 디렉터리 분석을 위한 개인 Python 도구 모음

회사생활에서 접한 반복 업무를 일반화해 개인적으로 다시 구현한 포트폴리오입니다. 여러 문서 집합을 일관된 방식으로 살피고 정리하는 작은 명령줄 도구를 제공합니다. 이 저장소에는 외부 조직의 코드, 데이터, 로고, 내부 경로가 포함되어 있지 않으며, 예제와 테스트에는 합성 데이터만 사용합니다.

## ✨ 주요 기능

| 기능 | 설명 |
| --- | --- |
| `numbers` | 정수 목록의 누락 값, 중복 값, 비정상 행을 찾습니다. |
| `duplicates` | 텍스트 목록에서 두 번 이상 나온 이름과 횟수를 정렬해 보여 줍니다. |
| `compare` | 기대 파일 목록과 실제 디렉터리를 재귀적으로 비교합니다. |
| `tree` | 디렉터리 구조를 텍스트 또는 이모지 트리로 출력하고 CSV로 저장합니다. |
| `doc-utils` | 위 기능을 일관된 명령 형식으로 실행합니다. |

## 🧭 설계 방향

- 반복되는 확인 작업을 작고 조합 가능한 명령으로 나눕니다.
- 입력과 출력의 규칙을 단순하게 유지해 자동화 흐름에 연결하기 쉽게 만듭니다.
- 재현 가능한 예제와 테스트를 통해 동작을 검증합니다.
- 포트폴리오 범위에 맞춰 독립적으로 구현하고, 출처와 데이터 경계를 문서화합니다.

## 🛠 기술 스택

| Category | 기술 |
| --- | --- |
| Language | Python 3.11+ |
| Package management | uv |
| Build | Hatchling |
| Test | pytest |
| Lint | Ruff |
| Interface | CLI (`doc-utils`) |

## 🔍 기술 선정 이유

Python은 텍스트와 경로를 다루는 유틸리티를 빠르게 구성하고 읽기 쉽게 유지하기에 적합합니다. `uv`는 개발 환경과 의존성 설치 과정을 간결하게 만들며, pytest와 Ruff는 동작 검증 및 기본 품질 검사를 자동화합니다. Hatchling은 가벼운 패키지 빌드 구성을 제공합니다.

## 📁 프로젝트 구조

```text
.
├── src/document_workflow_utils/  # 패키지와 CLI 구현
├── tests/                       # 합성 데이터를 사용하는 테스트
├── docs/                        # 출처 및 사용 안내 문서
├── pyproject.toml               # 패키지와 개발 도구 설정
└── README.md
```

## 🚀 시작하기

### 요구사항

- Python 3.11 이상
- [uv](https://docs.astral.sh/uv/)

### Clone

```bash
git clone https://github.com/jaehunshin-git/document-workflow-utils.git
cd document-workflow-utils
```

### 설정

```bash
uv sync --group dev
```

### 실행

```bash
uv run doc-utils numbers ./numbers.txt
uv run doc-utils duplicates ./names.txt
uv run doc-utils compare ./expected.txt ./documents
uv run doc-utils tree ./documents --mode text
```

### 검증

```bash
uv run pytest
uv run ruff check src tests
uv build
```

## 📚 문서

- [출처 및 구현 경계](docs/provenance.md): 독립 구현 원칙, 포함·제외 범위, 합성 데이터 정책

## 🤝 협업 규칙

### Branch

`<type>/<topic>`

```text
feat/directory-summary
```

### Commit Message

`<type>(<scope>): <한국어 요약>`

```text
feat(files): 디렉터리 요약 기능 추가
```

## 📄 이용 안내

이 저장소는 오픈소스 라이선스를 제공하지 않으며, 모든 권리를 유보합니다. 명시적인 사전 허가 없이 이 저장소의 코드와 문서를 복제, 수정, 재배포하거나 상업적으로 이용할 수 없습니다.
