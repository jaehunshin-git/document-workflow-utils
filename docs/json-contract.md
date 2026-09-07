# JSON 출력 계약

이 문서는 `doc-utils` 0.3 계열이 제공하는 JSON 출력의 공개 계약을 설명합니다. 모든 JSON은 UTF-8로 출력되며 키를 결정적으로 정렬합니다.

## 공통 필드

모든 명령의 JSON 최상위 객체에는 다음 필드가 포함됩니다.

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `schema_version` | string | JSON 계약 버전입니다. 현재 값은 `1.0`입니다. |
| `command` | string | 결과를 만든 하위 명령입니다. |

`schema_version`의 주 버전이 바뀌면 기존 소비 코드에 호환되지 않는 변경이 있을 수 있습니다. 같은 주 버전에서는 기존 필드의 의미와 타입을 유지하며, 새 필드가 추가될 수 있습니다.

## `numbers`

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `valid_count` | integer | 유효한 정수 행의 수 |
| `invalid_count` | integer | 정수로 해석할 수 없는 행의 수 |
| `invalid_lines` | array | `line`과 원문 `value`를 담은 객체 목록 |
| `minimum` | integer 또는 null | 유효 정수의 최솟값 |
| `maximum` | integer 또는 null | 유효 정수의 최댓값 |
| `missing` | integer array | 최솟값과 최댓값 사이의 누락 값 |
| `duplicates` | integer array | 두 번 이상 나온 값 |

유효한 정수가 하나 이상이면 종료 코드 `0`, 없으면 `1`입니다.

```json
{
  "command": "numbers",
  "duplicates": [103],
  "invalid_count": 1,
  "invalid_lines": [{"line": 6, "value": "invalid-value"}],
  "maximum": 105,
  "minimum": 100,
  "missing": [102, 104],
  "schema_version": "1.0",
  "valid_count": 5
}
```

## `duplicates`

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `duplicate_count` | integer | 중복된 고유 이름의 수 |
| `duplicates` | object | 이름을 키, 등장 횟수를 값으로 갖는 객체 |

정상적으로 입력을 읽었다면 중복 존재 여부와 관계없이 종료 코드 `0`입니다.

## `compare`

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `expected_count` | integer | 정규화와 제외 규칙을 적용한 기대 파일 수 |
| `actual_count` | integer | 디렉터리에서 발견한 실제 파일 수 |
| `missing` | string array | 기대 목록에는 있으나 실제로 없는 상대경로 |
| `unexpected` | string array | 실제로 있으나 기대 목록에는 없는 상대경로 |
| `matches` | boolean | 누락과 추가가 모두 없는지 여부 |

기본 모드에서는 누락 파일이 있으면 종료 코드 `1`입니다. `--strict`에서는 누락 또는 추가 파일이 하나라도 있으면 `1`입니다. 비교를 완료했다는 사실과 검증 성공 여부를 함께 전달하기 위해 종료 코드가 `1`이어도 JSON 결과는 표준 출력에 제공합니다.

## `tree`

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `root` | string | 분석한 루트 디렉터리 이름 |
| `mode` | string | `text` 또는 `emoji` |
| `directory_count` | integer | 포함된 디렉터리 수 |
| `file_count` | integer | 포함된 파일 수 |
| `extension_counts` | object | 정규화된 확장자별 파일 수 |
| `entries` | array | 각 항목의 `path`, `type`, `depth`를 담은 객체 목록 |

정상적으로 디렉터리를 분석했다면 종료 코드 `0`입니다.

확장자는 파일명의 마지막 점을 기준으로 소문자화합니다. 다중 확장자 파일은 마지막 확장자에 집계하고, 확장자가 없거나 `.env`처럼 이름 전체가 점으로 시작하는 파일은 빈 문자열 키(`""`)에 집계합니다.

## 오류 계약

인자 사용 오류, 잘못된 경로 계약, 파일 입출력 오류는 종료 코드 `2`를 사용합니다. 이 경우 JSON 객체를 일부 성공 결과처럼 출력하지 않고, `오류:`로 시작하는 설명을 표준 오류에 출력합니다. `argparse`가 감지한 잘못된 옵션도 종료 코드 `2`입니다.
